"""
StageExecutor — ALIVE 스테이지 BI-EXEC 지시자 파서 및 실행 엔진

MD 파일에서 <!-- BI-EXEC: {"tool": "...", "args": {...}} --> 지시자를 파싱하여
ToolRegistry.execute()를 통해 실행하고, 결과를 <!-- RESULT --> 블록으로 기록합니다.
이전 스테이지의 RESULT 블록을 현재 스테이지에 컨텍스트로 주입합니다.
"""
import re
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class FileLockedError(Exception):
    """스테이지 파일이 에디터에 의해 잠겨있을 때 발생합니다."""
    pass


class StageExecutor:
    """MD 파일의 BI-EXEC JSON 지시자를 파싱하고 ToolRegistry를 통해 실행합니다."""

    # <!-- BI-EXEC: {"tool": "...", "args": {...}} -->
    BI_EXEC_PATTERN = re.compile(
        r'<!-- BI-EXEC:\s*(\{.*?\})\s*-->',
        re.DOTALL
    )
    # <!-- RESULT:START -->...<!-- RESULT:END -->
    RESULT_BLOCK = re.compile(
        r'<!-- RESULT:START -->.*?<!-- RESULT:END -->',
        re.DOTALL
    )

    def __init__(self, registry, context: Dict[str, Any] = None):
        """
        Args:
            registry: ToolRegistry 인스턴스 (AgenticOrchestrator.registry 프로퍼티로 접근)
            context: 실행 컨텍스트 (active_connection 등)
        """
        self.registry = registry
        self.context = context or {}

    def execute_stage(self, md_path: Path, prior_stage_files: List[Path] = None) -> str:
        """스테이지 MD 파일의 모든 BI-EXEC 블록을 실행하고 결과를 기록합니다.

        Args:
            md_path: 현재 스테이지 MD 파일 경로
            prior_stage_files: 이전 스테이지 파일 경로 목록 (크로스 스테이지 컨텍스트용)

        Returns:
            업데이트된 파일 내용

        Raises:
            FileLockedError: .lock 센티넬 파일이 존재할 경우
        """
        # 파일 잠금 체크
        lock_path = Path(str(md_path) + '.lock')
        if lock_path.exists():
            raise FileLockedError(
                f"파일이 잠겨있습니다 (에디터가 열어두었을 수 있음): {lock_path}\n"
                f"에디터를 닫고 {lock_path}를 삭제한 후 다시 시도하세요."
            )

        content = md_path.read_text(encoding='utf-8')

        # 이전 스테이지 컨텍스트 주입
        if prior_stage_files:
            prior_context = self._collect_prior_results(prior_stage_files)
            if prior_context:
                content = self._inject_prior_context(content, prior_context)

        # 모든 BI-EXEC 블록 실행
        # re.finditer는 겹치지 않는 매치를 순서대로 반환
        # content가 수정되므로 매번 re-scan
        executed_count = 0
        max_iterations = 50  # 무한루프 방지

        for _ in range(max_iterations):
            match = self.BI_EXEC_PATTERN.search(content)
            if not match:
                break

            json_str = match.group(1)
            try:
                directive = json.loads(json_str)
                tool_name = directive["tool"]
                args = directive.get("args", {})
                logger.info(f"BI-EXEC 실행: {tool_name}({args})")
                result = self.registry.execute(tool_name, args, context=self.context)
                if result is None:
                    result = "(결과 없음)"
                result = str(result)
            except json.JSONDecodeError as e:
                result = f"[오류] 잘못된 BI-EXEC JSON: {e}"
                logger.error(f"BI-EXEC JSON 파싱 오류: {e}, json_str={json_str}")
            except KeyError:
                result = "[오류] BI-EXEC JSON에 'tool' 필드가 없습니다"
                logger.error(f"BI-EXEC 'tool' 필드 누락: {json_str}")
            except Exception as e:
                result = f"[오류] {type(e).__name__}: {e}"
                logger.error(f"BI-EXEC 실행 오류: {e}", exc_info=True)

            content = self._insert_result(content, match, result)
            executed_count += 1

        if executed_count > 0:
            md_path.write_text(content, encoding='utf-8')
            logger.info(f"{executed_count}개 BI-EXEC 블록 실행 완료: {md_path}")

        return content

    def _collect_prior_results(self, prior_files: List[Path]) -> str:
        """이전 스테이지 파일들의 RESULT 블록을 수집하고 연결합니다."""
        results = []
        for f in prior_files:
            if not f.exists():
                continue
            try:
                text = f.read_text(encoding='utf-8')
                # 파일 이름에서 스테이지 이름 추출 (예: 01-ask.md -> ASK)
                stem = f.stem  # "01-ask"
                if '-' in stem:
                    stage_name = stem.split('-', 1)[1].upper()
                else:
                    stage_name = stem.upper()

                for m in self.RESULT_BLOCK.finditer(text):
                    block = m.group(0)
                    inner = (block
                             .replace('<!-- RESULT:START -->', '')
                             .replace('<!-- RESULT:END -->', '')
                             .strip())
                    if inner and inner not in ('', '(결과 없음)'):
                        results.append(f"**[{stage_name}]**\n{inner}")
            except Exception as e:
                logger.warning(f"이전 스테이지 파일 읽기 실패: {f}: {e}")

        return "\n\n".join(results)

    def _inject_prior_context(self, content: str, prior_context: str) -> str:
        """'## Context from Prior Stages' 섹션에 이전 스테이지 컨텍스트를 주입합니다."""
        marker = "## Context from Prior Stages"
        if marker not in content:
            return content

        # 마커 다음 줄의 자동주입 주석을 실제 컨텍스트로 교체
        auto_comment = "<!-- StageExecutor가 이전 스테이지 RESULT 블록을 자동 주입합니다 -->"

        if auto_comment in content:
            content = content.replace(
                f"{marker}\n{auto_comment}",
                f"{marker}\n{prior_context}"
            )
        else:
            # 주석이 없으면 마커 다음 줄에 삽입
            idx = content.find(marker)
            end_of_line = content.find('\n', idx) + 1
            content = content[:end_of_line] + prior_context + "\n\n" + content[end_of_line:]

        return content

    def _insert_result(self, content: str, match: re.Match, result: str) -> str:
        """BI-EXEC 주석 다음에 RESULT 블록을 삽입하거나 교체합니다."""
        exec_end = match.end()
        result_block = f"\n<!-- RESULT:START -->\n{result}\n<!-- RESULT:END -->"

        # BI-EXEC 다음에 이미 RESULT 블록이 있는지 확인
        after_exec = content[exec_end:]
        existing = self.RESULT_BLOCK.search(after_exec)

        if existing and after_exec[:existing.start()].strip() == '':
            # 기존 RESULT 블록 교체
            abs_start = exec_end + existing.start()
            abs_end = exec_end + existing.end()
            content = content[:abs_start] + result_block + content[abs_end:]
        else:
            # 새 RESULT 블록 삽입
            content = content[:exec_end] + result_block + content[exec_end:]

        return content

    def has_bi_exec_blocks(self, md_path: Path) -> bool:
        """MD 파일에 실행 대기 중인 BI-EXEC 블록이 있는지 확인합니다."""
        if not md_path.exists():
            return False
        content = md_path.read_text(encoding='utf-8')
        return bool(self.BI_EXEC_PATTERN.search(content))

    def count_bi_exec_blocks(self, md_path: Path) -> int:
        """MD 파일의 BI-EXEC 블록 수를 반환합니다."""
        if not md_path.exists():
            return 0
        content = md_path.read_text(encoding='utf-8')
        return len(self.BI_EXEC_PATTERN.findall(content))
