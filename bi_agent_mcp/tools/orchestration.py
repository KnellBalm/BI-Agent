"""분석 오케스트레이션 도구 — 막연한 분석 요구를 구조화된 워크플로우로 관리."""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path.home() / ".bi-agent-mcp"
_PLANS_DIR = _CONFIG_DIR / "analysis_plans"
_MAX_STEPS = 50  # soft cap

_VALID_TRANSITIONS = {
    "pending": {"in_progress", "skipped"},
    "in_progress": {"completed", "skipped", "pending"},
    "completed": {"in_progress"},  # 재오픈 허용
    "skipped": {"pending"},
}
_VALID_STEP_STATUSES = {"pending", "in_progress", "completed", "skipped"}
_VALID_PLAN_STATUSES = {"in_progress", "completed", "abandoned"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _plan_path(plan_id: str) -> Path:
    return _PLANS_DIR / f"{plan_id}.json"


def _load_plan(plan_id: str) -> tuple[dict | None, str]:
    path = _plan_path(plan_id)
    if not path.exists():
        return None, f"[ERROR] 플랜 ID '{plan_id}'를 찾을 수 없습니다."
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except Exception as e:
        return None, f"[ERROR] 플랜 파일 읽기 실패: {e}"


def _save_plan(plan: dict) -> str:
    """저장 후 빈 문자열 반환. 오류 시 [ERROR] 문자열."""
    try:
        _PLANS_DIR.mkdir(parents=True, exist_ok=True)
        _plan_path(plan["plan_id"]).write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return ""
    except Exception as e:
        return f"[ERROR] 플랜 저장 실패: {e}"


def _progress_str(plan: dict) -> str:
    steps = plan.get("steps", [])
    done = sum(1 for s in steps if s["status"] in ("completed", "skipped"))
    return f"{done}/{len(steps)}"


def _render_plan(plan: dict) -> str:
    lines = [
        f"## 분석 플랜: {plan['goal']}",
        f"- **ID**: `{plan['plan_id']}`",
        f"- **상태**: {plan['status']}",
        f"- **진행률**: {_progress_str(plan)} 단계",
        f"- **생성**: {plan.get('created_at', '')}  **수정**: {plan.get('updated_at', '')}",
    ]
    if plan.get("tags"):
        lines.append(f"- **태그**: {', '.join(plan['tags'])}")
    if plan.get("context"):
        lines.append(f"\n**컨텍스트**: {plan['context'][:300]}")

    steps = plan.get("steps", [])
    if steps:
        lines.append("\n### 분석 단계")
        lines.append("| # | 제목 | 상태 | 권장 도구 | 발견사항 미리보기 |")
        lines.append("|---|------|------|-----------|------------------|")
        for s in steps:
            hints = ", ".join(s.get("tools_hint", []))
            findings_preview = (s.get("findings") or "")[:60].replace("\n", " ")
            lines.append(
                f"| {s['idx']} | {s['title']} | {s['status']} | {hints} | {findings_preview} |"
            )

    if plan.get("summary"):
        lines.append(f"\n### 종합 요약\n{plan['summary']}")

    return "\n".join(lines)


def create_analysis_plan(
    goal: str,
    context: str = "",
    steps: list = None,
    tags: list = None,
) -> str:
    """[Orchestration] 분석 플랜을 생성하고 plan_id를 발급합니다.

    Args:
        goal: 분석 목표 (예: "이번 달 매출 하락 원인 파악")
        context: 데이터 컨텍스트 (테이블명, 스키마 정보 등)
        steps: 초기 분석 단계 목록. 각 항목은 {"title": str, "description": str, "tools_hint": list[str]} 형식.
               생략 시 빈 플랜으로 시작.
        tags: 분류 태그 목록 (예: ["매출", "원인분석"])

    Returns:
        plan_id와 플랜 요약 (Markdown)
    """
    if not goal.strip():
        return "[ERROR] goal은 필수 입력값입니다."

    # plan_id 생성 (충돌 방지)
    _PLANS_DIR.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        plan_id = uuid.uuid4().hex[:8]
        if not _plan_path(plan_id).exists():
            break
    else:
        return "[ERROR] plan_id 생성에 실패했습니다. 다시 시도하세요."

    now = _now()
    step_list = []
    for i, s in enumerate(steps or []):
        step_list.append({
            "idx": i,
            "title": s.get("title", f"단계 {i}"),
            "description": s.get("description", ""),
            "status": "pending",
            "tools_hint": s.get("tools_hint", []),
            "findings": "",
            "queries_used": [],
            "started_at": None,
            "completed_at": None,
            "updated_at": now,
        })

    plan = {
        "plan_id": plan_id,
        "goal": goal,
        "context": context,
        "status": "in_progress",
        "created_at": now,
        "updated_at": now,
        "tags": tags or [],
        "steps": step_list,
        "summary": "",
    }

    err = _save_plan(plan)
    if err:
        return err

    return f"플랜 생성 완료 (ID: `{plan_id}`)\n\n" + _render_plan(plan)


def get_analysis_plan(plan_id: str) -> str:
    """[Orchestration]
    분석 플랜의 현재 상태를 Markdown으로 반환합니다.

    Args:
        plan_id: 조회할 플랜 ID

    Returns:
        플랜 상태 Markdown (목표, 진행률, 단계별 상태, 발견사항)
    """
    plan, err = _load_plan(plan_id)
    if err:
        return err
    return _render_plan(plan)


def update_analysis_step(
    plan_id: str,
    step_idx: int,
    status: str,
    findings: str = "",
    queries_used: list = None,
) -> str:
    """[Orchestration] 분석 단계의 상태와 발견사항을 업데이트합니다.

    Args:
        plan_id: 플랜 ID
        step_idx: 업데이트할 단계 인덱스 (0부터 시작)
        status: 새 상태 ("pending" | "in_progress" | "completed" | "skipped")
        findings: 이 단계에서 발견한 내용 (Markdown 자유 형식)
        queries_used: 이 단계에서 실행한 SQL 목록 (선택)

    Returns:
        업데이트된 단계 요약 + 전체 진행률
    """
    plan, err = _load_plan(plan_id)
    if err:
        return err

    if status not in _VALID_STEP_STATUSES:
        return f"[ERROR] 유효하지 않은 status '{status}'. 사용 가능: {sorted(_VALID_STEP_STATUSES)}"

    steps = plan.get("steps", [])
    if step_idx < 0 or step_idx >= len(steps):
        return f"[ERROR] step_idx {step_idx}가 범위를 벗어났습니다. 총 {len(steps)}개 단계."

    step = steps[step_idx]
    current = step["status"]
    allowed = _VALID_TRANSITIONS.get(current, set())
    warning = ""
    if status not in allowed:
        warning = f"\n⚠️ 상태 전이 경고: '{current}' → '{status}'는 비표준 전이입니다."

    now = _now()
    step["status"] = status
    if findings:
        step["findings"] = findings
    if queries_used is not None:
        step["queries_used"] = queries_used
    step["updated_at"] = now
    if status == "in_progress" and not step.get("started_at"):
        step["started_at"] = now
    if status in ("completed", "skipped"):
        step["completed_at"] = now

    plan["updated_at"] = now
    err = _save_plan(plan)
    if err:
        return err

    return (
        f"단계 {step_idx} '{step['title']}' → **{status}** 업데이트됨\n"
        f"진행률: {_progress_str(plan)} 단계{warning}"
    )


def add_analysis_step(
    plan_id: str,
    title: str,
    description: str = "",
    tools_hint: list = None,
    insert_after: int = None,
) -> str:
    """[Orchestration] 분석 플랜에 새 단계를 동적으로 추가합니다.

    Args:
        plan_id: 플랜 ID
        title: 단계 제목
        description: 단계 설명
        tools_hint: 이 단계에서 사용할 권장 도구 목록 (예: ["trend_analysis", "run_query"])
        insert_after: 삽입 위치 (해당 인덱스 다음에 삽입). 생략 시 마지막에 추가.

    Returns:
        추가된 단계 정보 + 전체 플랜 요약
    """
    plan, err = _load_plan(plan_id)
    if err:
        return err

    steps = plan.get("steps", [])
    if len(steps) >= _MAX_STEPS:
        return f"[ERROR] 단계 수가 최대({_MAX_STEPS}개)에 도달했습니다."

    now = _now()
    new_step = {
        "title": title,
        "description": description,
        "status": "pending",
        "tools_hint": tools_hint or [],
        "findings": "",
        "queries_used": [],
        "started_at": None,
        "completed_at": None,
        "updated_at": now,
    }

    if insert_after is None or insert_after >= len(steps):
        steps.append(new_step)
    elif insert_after < 0:
        steps.insert(0, new_step)
    else:
        steps.insert(insert_after + 1, new_step)

    # idx 재정렬
    for i, s in enumerate(steps):
        s["idx"] = i

    plan["steps"] = steps
    plan["updated_at"] = now
    err = _save_plan(plan)
    if err:
        return err

    new_idx = next(i for i, s in enumerate(steps) if s["title"] == title and s["status"] == "pending")
    return (
        f"단계 {new_idx} '{title}' 추가됨\n"
        f"전체 {len(steps)}개 단계\n\n" + _render_plan(plan)
    )


def synthesize_findings(plan_id: str, format: str = "summary") -> str:
    """[Orchestration] 플랜 내 모든 completed 단계의 발견사항을 구조화하여 반환합니다.
    (이 도구는 발견사항을 수집·구조화만 하며, 결론 도출은 Claude가 담당합니다.)

    Args:
        plan_id: 플랜 ID
        format: 출력 형식 ("summary" | "detailed" | "executive")
                - summary: 단계별 발견사항 목록
                - detailed: 단계별 발견사항 + 사용 쿼리 포함
                - executive: 경영진 보고용 간결 구조 (단계 요약 1줄씩)

    Returns:
        구조화된 발견사항 Markdown (Claude가 최종 인사이트를 생성하기 위한 입력)
    """
    plan, err = _load_plan(plan_id)
    if err:
        return err

    if format not in ("summary", "detailed", "executive"):
        return "[ERROR] format은 'summary', 'detailed', 'executive' 중 하나여야 합니다."

    steps = plan.get("steps", [])
    completed = [s for s in steps if s["status"] == "completed" and s.get("findings")]

    if not completed:
        return f"[INFO] 완료된 단계의 발견사항이 없습니다. (플랜: {plan['goal']})"

    lines = [
        f"# 분석 발견사항 종합",
        f"**목표**: {plan['goal']}",
        f"**플랜 ID**: `{plan_id}`",
        f"**완료 단계**: {len(completed)}/{len(steps)}",
        "",
    ]

    if format == "executive":
        lines.append("## 단계별 핵심 발견사항 (요약)")
        for s in completed:
            first_line = (s.get("findings") or "").split("\n")[0][:120]
            lines.append(f"- **{s['title']}**: {first_line}")
    elif format == "summary":
        lines.append("## 단계별 발견사항")
        for s in completed:
            lines.append(f"\n### {s['idx']}. {s['title']}")
            lines.append(s.get("findings", ""))
    else:  # detailed
        lines.append("## 단계별 발견사항 (상세)")
        for s in completed:
            lines.append(f"\n### {s['idx']}. {s['title']}")
            lines.append(s.get("findings", ""))
            if s.get("queries_used"):
                lines.append("\n**사용 쿼리:**")
                for q in s["queries_used"]:
                    lines.append(f"```sql\n{q}\n```")

    lines.append("\n---")
    lines.append("*위 발견사항을 바탕으로 종합 인사이트와 결론을 도출하세요.*")

    result = "\n".join(lines)

    # summary 필드 업데이트
    plan["summary"] = result
    plan["updated_at"] = _now()
    _save_plan(plan)

    return result


def list_analysis_plans(
    status: str = "all",
    limit: int = 20,
    tags: list = None,
) -> str:
    """
    [Orchestration] 저장된 분석 플랜 목록을 반환합니다.

    Args:
        status: 필터 ("all" | "in_progress" | "completed" | "abandoned")
        limit: 반환할 최대 플랜 수 (기본 20)
        tags: 태그 필터 (AND 조건, 선택)

    Returns:
        플랜 목록 Markdown 테이블
    """
    if not _PLANS_DIR.exists():
        return "저장된 분석 플랜이 없습니다."

    plans = []
    for f in sorted(_PLANS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            plan = json.loads(f.read_text(encoding="utf-8"))
            plans.append(plan)
        except Exception:
            continue

    if status != "all":
        plans = [p for p in plans if p.get("status") == status]
    if tags:
        plans = [p for p in plans if all(t in p.get("tags", []) for t in tags)]

    plans = plans[:limit]

    if not plans:
        return "조건에 맞는 분석 플랜이 없습니다."

    lines = ["| ID | 목표 | 상태 | 진행률 | 태그 | 생성일 |",
             "|----|------|------|--------|------|--------|"]
    for p in plans:
        tag_str = ", ".join(p.get("tags", []))
        lines.append(
            f"| `{p['plan_id']}` | {p['goal'][:40]} | {p['status']} "
            f"| {_progress_str(p)} | {tag_str} | {p.get('created_at', '')[:10]} |"
        )
    return "\n".join(lines)


def complete_analysis_plan(plan_id: str, final_status: str = "completed") -> str:
    """
    [Orchestration] 분석 플랜을 종료합니다.

    Args:
        plan_id: 종료할 플랜 ID
        final_status: "completed" | "abandoned" (기본: "completed")

    Returns:
        최종 상태 요약
    """
    plan, err = _load_plan(plan_id)
    if err:
        return err

    if final_status not in ("completed", "abandoned"):
        return "[ERROR] final_status는 'completed' 또는 'abandoned'여야 합니다."

    steps = plan.get("steps", [])
    pending = [s for s in steps if s["status"] in ("pending", "in_progress")]
    warning = ""
    if pending and final_status == "completed":
        titles = ", ".join(s["title"] for s in pending[:3])
        warning = f"\n⚠️ 미완료 단계 {len(pending)}개 있음: {titles}"

    plan["status"] = final_status
    plan["updated_at"] = _now()
    err = _save_plan(plan)
    if err:
        return err

    return (
        f"플랜 '{plan['goal']}' → **{final_status}** 완료\n"
        f"진행률: {_progress_str(plan)} 단계{warning}"
    )


def delete_analysis_plan(plan_id: str) -> str:
    """[Orchestration] 분석 플랜을 삭제합니다.

    Args:
        plan_id: 삭제할 플랜 ID

    Returns:
        삭제 결과 메시지
    """
    plan, err = _load_plan(plan_id)
    if err:
        return err

    try:
        _plan_path(plan_id).unlink()
        return f"플랜 '{plan['goal']}' (ID: `{plan_id}`) 삭제됨"
    except Exception as e:
        return f"[ERROR] 플랜 삭제 실패: {e}"
