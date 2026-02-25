"""
AnalysisManager — ALIVE 분석 생명주기 관리 모듈

alive-analysis 방법론(Ask→Look→Investigate→Voice→Evolve)을 기반으로
분석 폴더, _meta.yaml, 스테이지 MD 파일의 생성/전환/보관을 담당합니다.

AaCOrchestrator와 독립적으로 동작합니다. 기존 plan.md 워크플로우에 영향 없음.
"""
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, List

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from backend.aac.plan_parser import AnalysisStage, AnalysisProject  # type: ignore

from backend.aac.templates.ask import render as render_ask
from backend.aac.templates.quick import render as render_quick

# ALIVE stage state machine: each stage maps to its successor
_STAGE_TRANSITIONS = {
    AnalysisStage.ASK: AnalysisStage.LOOK,
    AnalysisStage.LOOK: AnalysisStage.INVESTIGATE,
    AnalysisStage.INVESTIGATE: AnalysisStage.VOICE,
    AnalysisStage.VOICE: AnalysisStage.EVOLVE,
}

# Map stage enum to the filename prefix used for stage markdown files
_STAGE_FILENAME = {
    AnalysisStage.ASK: "01-ask.md",
    AnalysisStage.LOOK: "02-look.md",
    AnalysisStage.INVESTIGATE: "03-investigate.md",
    AnalysisStage.VOICE: "04-voice.md",
    AnalysisStage.EVOLVE: "05-evolve.md",
}


def _yaml_dump(data: dict) -> str:
    """Dump dict to YAML string, with fallback to manual key:value writing."""
    if HAS_YAML:
        return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    # Fallback: simple key: value (handles str, list, None)
    lines = []
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item!r}")
        elif v is None:
            lines.append(f"{k}: null")
        else:
            lines.append(f"{k}: {v!r}")
    return "\n".join(lines) + "\n"


def _yaml_load(text: str) -> dict:
    """Load YAML string to dict, with fallback to simple key: value parsing."""
    if HAS_YAML:
        result = yaml.safe_load(text)
        return result if isinstance(result, dict) else {}
    # Fallback: very basic key: value parser (no nested structures)
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            result[k.strip()] = v.strip().strip('"').strip("'")
    return result


class AnalysisManager:
    """ALIVE 분석 생명주기 관리 클래스.

    분석 폴더, _meta.yaml, 스테이지 MD 파일의 생성/전환/보관을 담당합니다.
    """

    def __init__(self, base_dir: str = "analyses") -> None:
        self.base_dir = Path(base_dir)
        self.quick_dir = self.base_dir / "quick"
        self.archived_dir = self.base_dir / "_archived"

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.quick_dir.mkdir(parents=True, exist_ok=True)
        self.archived_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_analysis(
        self,
        title: str,
        connection: str = "",
        type: str = "full",
    ) -> "AnalysisProject":
        """새 full 분석을 생성하고 AnalysisProject를 반환합니다.

        - ID: A-YYYY-MMDD-NNN 형식 (기존 분석 수 기준으로 NNN 자동 증가)
        - 폴더명: slugified title
        - _meta.yaml, 01-ask.md 생성
        """
        analysis_id = self._generate_id("A")
        slug = self._slugify(title)
        folder = self.base_dir / slug
        folder.mkdir(parents=True, exist_ok=True)

        now = datetime.now().isoformat(timespec="seconds")
        project = AnalysisProject(
            id=analysis_id,
            title=title,
            type=type,
            status=AnalysisStage.ASK,
            created=now,
            updated=now,
            connection=connection,
            path=folder,
            data_sources=[],
            tags=[],
        )

        self._write_meta(project)

        # Create 01-ask.md from ask template
        ask_content = render_ask(
            title=title,
            date=now[:10],  # YYYY-MM-DD portion
            connection=connection,
        )
        (project.path / "01-ask.md").write_text(ask_content, encoding="utf-8")

        return project

    def create_quick(self, question: str = "", connection: str = "") -> Path:
        """Quick 분석 단일 파일을 analyses/quick/ 에 생성하고 Path를 반환합니다."""
        quick_id = self._generate_id("Q")
        filename = f"{quick_id}.md"
        filepath = self.quick_dir / filename

        content = render_quick(
            question=question,
            connection=connection,
            id=quick_id,
        )
        filepath.write_text(content, encoding="utf-8")
        return filepath

    def get_active(self) -> Optional["AnalysisProject"]:
        """가장 최근에 업데이트된 활성(archived 아님) 분석을 반환합니다.

        활성 분석이 없으면 None을 반환합니다.
        """
        projects = self.list_analyses()
        # list_analyses already filters out archived and sorts by updated desc
        if projects:
            return projects[0]
        return None

    def advance_stage(self, project: "AnalysisProject") -> "AnalysisStage":
        """분석을 다음 ALIVE 스테이지로 전환합니다.

        _meta.yaml의 status와 updated를 갱신하고, 새 스테이지 MD 파일을 생성합니다.
        EVOLVE 스테이지에서 호출하면 ValueError를 발생시킵니다.
        """
        current_stage = project.status
        if current_stage == AnalysisStage.EVOLVE:
            raise ValueError(
                f"분석 '{project.id}'은 이미 마지막 스테이지(EVOLVE)에 있습니다. "
                "더 이상 전환할 수 없습니다."
            )

        next_stage = _STAGE_TRANSITIONS[current_stage]
        now = datetime.now().isoformat(timespec="seconds")

        project.status = next_stage
        project.updated = now

        self._write_meta(project)

        # Create the next stage markdown file if the folder exists
        folder = project.path
        if folder.exists() and next_stage in _STAGE_FILENAME:
            stage_filename = _STAGE_FILENAME[next_stage]
            stage_file = folder / stage_filename
            if not stage_file.exists():
                stage_content = self._render_stage(project, next_stage)
                stage_file.write_text(stage_content, encoding="utf-8")

        return next_stage

    def list_analyses(self) -> List["AnalysisProject"]:
        """기존 full 분석 목록을 updated 내림차순으로 반환합니다.

        _archived, quick 디렉토리는 제외합니다.
        """
        projects: List[AnalysisProject] = []
        excluded = {"_archived", "quick"}

        for entry in self.base_dir.iterdir():
            if not entry.is_dir():
                continue
            if entry.name in excluded:
                continue
            meta_file = entry / "_meta.yaml"
            if not meta_file.exists():
                continue
            try:
                project = self._read_meta(entry)
                projects.append(project)
            except Exception:
                # Skip folders with malformed metadata
                continue

        projects.sort(key=lambda p: p.updated or "", reverse=True)
        return projects

    def archive(self, project: "AnalysisProject") -> None:
        """분석 폴더를 _archived/ 로 이동하고 status를 archived로 갱신합니다."""
        src = project.path
        dst = self.archived_dir / src.name

        # Update meta before moving so the archived copy reflects the status
        project.updated = datetime.now().isoformat(timespec="seconds")
        self._write_meta(project)

        # Move the folder
        src.rename(dst)
        project.path = dst

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _read_meta(self, folder: Path) -> "AnalysisProject":
        """_meta.yaml을 읽어 AnalysisProject를 반환합니다."""
        meta_file = folder / "_meta.yaml"
        if not meta_file.exists():
            raise FileNotFoundError(f"_meta.yaml not found in {folder}")

        text = meta_file.read_text(encoding="utf-8")
        data = _yaml_load(text)

        # Convert status string to AnalysisStage enum, default to ask
        raw_status = data.get("status", "ask")
        try:
            stage = AnalysisStage(raw_status)
        except (ValueError, KeyError):
            stage = AnalysisStage.ASK

        return AnalysisProject(
            id=data.get("id", ""),
            title=data.get("title", ""),
            type=data.get("type", "full"),
            status=stage,
            created=data.get("created", ""),
            updated=data.get("updated", ""),
            connection=data.get("connection", ""),
            path=folder,
            data_sources=data.get("data_sources") or [],
            tags=data.get("tags") or [],
        )

    def _write_meta(self, project: "AnalysisProject") -> None:
        """AnalysisProject를 _meta.yaml로 씁니다."""
        folder = project.path
        folder.mkdir(parents=True, exist_ok=True)

        # Convert AnalysisStage enum to its string value for YAML serialization
        status_str = project.status.value if hasattr(project.status, "value") else str(project.status)

        data = {
            "id": project.id,
            "title": project.title,
            "type": project.type,
            "status": status_str,
            "created": project.created,
            "updated": project.updated,
            "connection": project.connection,
            "data_sources": project.data_sources if project.data_sources else [],
            "tags": project.tags if project.tags else [],
        }

        meta_file = folder / "_meta.yaml"
        meta_file.write_text(_yaml_dump(data), encoding="utf-8")

    def _generate_id(self, prefix: str = "A") -> str:
        """ID를 생성합니다. 형식: {prefix}-YYYY-MMDD-NNN

        NNN은 기존 분석 수 + 1 (zero-padded 3자리).
        """
        today = datetime.now()
        date_str = today.strftime("%Y-%m%d")  # e.g. "2026-0224"

        # Count existing items to determine next NNN
        count = self._count_existing(prefix)
        seq = count + 1
        return f"{prefix}-{date_str}-{seq:03d}"

    def _count_existing(self, prefix: str) -> int:
        """prefix에 해당하는 기존 분석/quick 파일 수를 셉니다."""
        if prefix == "Q":
            # Count files in quick/ directory
            if not self.quick_dir.exists():
                return 0
            return sum(
                1 for f in self.quick_dir.iterdir()
                if f.is_file() and f.name.startswith("Q-")
            )
        else:
            # Count subdirs in base_dir that have _meta.yaml (includes archived)
            count = 0
            excluded = {"quick"}
            for d in self.base_dir.iterdir():
                if d.name in excluded:
                    continue
                if d.is_dir() and (d / "_meta.yaml").exists():
                    count += 1
            # Also count archived
            if self.archived_dir.exists():
                for d in self.archived_dir.iterdir():
                    if d.is_dir() and (d / "_meta.yaml").exists():
                        count += 1
            return count

    def _slugify(self, title: str) -> str:
        """타이틀을 URL-safe 슬러그로 변환합니다. 최대 50자."""
        slug = title.lower()
        # Replace spaces and special characters with hyphens
        slug = re.sub(r"[^a-z0-9가-힣]+", "-", slug)
        # Strip leading/trailing hyphens
        slug = slug.strip("-")
        # Truncate to 50 chars, then strip trailing hyphens again
        slug = slug[:50].rstrip("-")
        return slug or "analysis"

    def _render_stage(self, project: "AnalysisProject", stage: "AnalysisStage") -> str:
        """스테이지에 맞는 템플릿을 렌더링합니다."""
        date = (project.updated or datetime.now().isoformat())[:10]
        kwargs = dict(
            title=project.title,
            date=date,
            connection=project.connection,
            data_sources=project.data_sources,
        )

        if stage == AnalysisStage.LOOK:
            from backend.aac.templates.look import render as render_look
            return render_look(**kwargs)
        elif stage == AnalysisStage.INVESTIGATE:
            from backend.aac.templates.investigate import render as render_investigate
            return render_investigate(**kwargs)
        elif stage == AnalysisStage.VOICE:
            from backend.aac.templates.voice import render as render_voice
            return render_voice(**kwargs)
        elif stage == AnalysisStage.EVOLVE:
            from backend.aac.templates.evolve import render as render_evolve
            return render_evolve(**kwargs)
        else:
            return render_ask(**kwargs)
