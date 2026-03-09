"""
BI-Agent 명령어 트리 + 자동완성 엔진.

SlashCompleter: /로 시작하는 계층형 커맨드를 자동완성한다.
"""
from prompt_toolkit.completion import Completer, Completion


# ──────────────────────────────────────────────
# 계층형 명령어 트리 (Nested Command Tree)
# ──────────────────────────────────────────────

COMMAND_TREE: dict = {
    "/help":    {"meta": "Show this help message"},
    "/status":  {"meta": "Show current agent status (LLM, DB, Project)"},
    "/quit":    {"meta": "Exit the application"},
    "/exit":    {"meta": "Exit the application"},
    "/clear":   {"meta": "Clear the screen"},
    "/list":    {"meta": "Show connected data sources"},
    "/connect": {
        "meta": "Connect to a new data source",
        "children": {
            "sqlite": {"meta": "Connect to a SQLite database file"},
            "excel":  {"meta": "Connect to an Excel file"},
            "pg":     {"meta": "Connect to PostgreSQL database"},
        },
    },
    "/setting": {
        "meta": "Manage settings, API keys, OAuth login",
        "children": {
            "list":  {"meta": "Show current settings"},
            "set":   {
                "meta": "Update a setting value",
                "children": {
                    "gemini_key": {"meta": "Gemini API key"},
                    "claude_key": {"meta": "Claude API key"},
                    "openai_key": {"meta": "OpenAI API key"},
                    "model":      {"meta": "Default LLM model (e.g. gemini-2.5-flash)"},
                    "language":   {"meta": "Response language (ko, en, ja)"},
                },
            },
            "login": {
                "meta": "OAuth login to a provider",
                "children": {
                    "gemini": {"meta": "Google OAuth"},
                    "claude": {"meta": "Claude API key entry"},
                    "openai": {"meta": "OpenAI API key entry"},
                },
            },
            "help":  {"meta": "Show setting help details"},
        },
    },
    "/explore": {
        "meta": "Explore connected database",
        "children": {
            "schema":  {"meta": "Show table list or table details"},
            "query":   {"meta": "Execute a SQL SELECT query"},
            "preview": {"meta": "Preview top 10 rows of a table"},
        },
    },
    "/project": {
        "meta": "Manage analysis projects",
        "children": {
            "new":    {"meta": "Create a new project workspace"},
            "list":   {"meta": "List all projects"},
            "open":   {"meta": "Switch to another project"},
            "status": {"meta": "Show current project summary"},
        },
    },
    "/report": {
        "meta": "Manage markdown reports",
        "children": {
            "new":    {"meta": "Create a new report from template"},
            "list":   {"meta": "List reports in current project"},
            "show":   {"meta": "Display report contents"},
            "edit":   {"meta": "Open report in $EDITOR"},
            "append": {"meta": "Append a section to a report"},
        },
    },
    "/thinking":  {"meta": "Expand an idea into a markdown analysis plan"},
    "/run":       {"meta": "Execute an analysis from a markdown plan"},
    "/expert":    {"meta": "LangChain Expert mode deep-dive analysis"},
    "/init":      {"meta": "Generate plan.md template in current dir"},
    "/build":     {"meta": "Run the analysis pipeline from plan.md"},
    "/analysis": {
        "meta": "ALIVE analysis workflow",
        "children": {
            "new":     {"meta": "Create a new ALIVE analysis session"},
            "quick":   {"meta": "Run a quick single-file analysis"},
            "status":  {"meta": "Check current analysis status"},
            "list":    {"meta": "Show all analysis sessions"},
            "run":     {"meta": "Execute BI-EXEC block of current stage"},
            "next":    {"meta": "Transition to the next stage"},
            "archive": {"meta": "Archive the current analysis session"},
        },
    },
}

COMMAND_NAMES = list(COMMAND_TREE.keys())


class SlashCompleter(Completer):
    """/로 시작하는 계층형 명령어 자동완성 엔진."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return

        parts = text.split()
        trailing_space = text.endswith(" ")

        if not trailing_space and len(parts) <= 1:
            # 1-depth: 메인 명령어 매칭
            word = parts[0] if parts else "/"
            for cmd, node in COMMAND_TREE.items():
                if cmd.startswith(word):
                    yield Completion(
                        cmd,
                        start_position=-len(word),
                        display=cmd,
                        display_meta=node.get("meta", ""),
                    )
        else:
            # 2-depth 이상: 부모 노드를 찾아서 children 제안
            main_cmd = parts[0]
            node = COMMAND_TREE.get(main_cmd)
            if not node or "children" not in node:
                return

            children = node["children"]
            depth_parts = parts[1:]

            while len(depth_parts) > 1 or (len(depth_parts) == 1 and trailing_space):
                if not depth_parts:
                    break
                token = depth_parts[0]
                child_node = children.get(token)
                if child_node and "children" in child_node:
                    children = child_node["children"]
                    depth_parts = depth_parts[1:]
                else:
                    if trailing_space and len(depth_parts) == 1:
                        child_node = children.get(depth_parts[0])
                        if child_node and "children" in child_node:
                            children = child_node["children"]
                            depth_parts = []
                        else:
                            return
                    else:
                        break

            word = depth_parts[0] if depth_parts else ""
            for sub, sub_node in children.items():
                if sub.startswith(word):
                    yield Completion(
                        sub,
                        start_position=-len(word),
                        display=sub,
                        display_meta=sub_node.get("meta", ""),
                    )
