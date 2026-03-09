"""
BI-Agent TUI Layout — prompt_toolkit full-screen Application.

고정 헤더 + 스크롤 출력 + 고정 입력창 3-panel 레이아웃을 제공한다.
"""
from prompt_toolkit.formatted_text import ANSI


# ──────────────────────────────────────────────
# Header Builder
# ──────────────────────────────────────────────

def build_header_text(
    version: str = "v0.1.1",
    model: str = "?",
    auth: str = "미설정",
    db: str = "연결 없음",
    cwd: str = "",
) -> str:
    """ANSI 컬러가 포함된 헤더 텍스트 문자열을 반환한다."""
    cwd_short = cwd if len(cwd) <= 50 else "~/" + cwd.split("/")[-1]

    lines = [
        f" \033[36m     (◉)\033[0m           \033[1;36mBI-Agent\033[0m {version}",
        f" \033[0m    /   \\\033[0m          \033[36m{model}\033[0m · {auth}",
        f" \033[33m  (◉)\033[0m───\033[32m(◉)\033[0m        {db}",
        f" \033[2mOrchestrating Intelligence · {cwd_short}\033[0m",
    ]
    return "\n".join(lines)
