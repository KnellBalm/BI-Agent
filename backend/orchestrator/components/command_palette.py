from textual.app import App
from textual.widgets import OptionList
from textual.widgets.option_list import Option

class CommandPalette:
    """
    명령어 팔레트 UI 및 필터링 로직을 담당하는 컴포넌트
    """
    def __init__(self, app: App):
        self.app = app
        self.visible = False
        self.commands = [
            ("/login", "LLM Provider 인증 설정", "cmd_login"),
            ("/connect", "데이터 소스 연결 관리", "cmd_connect"),
            ("/project", "프로젝트 전환/생성", "cmd_project"),
            ("/explore", "데이터 테이블 탐색 및 선택", "cmd_explore"),
            ("/analyze", "현재 상황에 대한 AI 분석 수행", "cmd_analyze"),
            ("/search", "데이터 정보/스키마 검색", "cmd_search"),
            ("/clear", "채팅 화면 초기화", "cmd_clear"),
            ("/history", "명령어 실행 히스토리 보기", "cmd_history"),
            ("/help", "명령어 및 단축키 안내", "cmd_help"),
            ("/quit", "애플리케이션 종료", "cmd_quit"),
            ("/exit", "애플리케이션 종료", "cmd_exit")
        ]

    def update(self, filter_text: str = ""):
        """현재 입력값에 따라 명령 메뉴 항목을 필터링하여 업데이트"""
        menu = self.app.query_one("#command-menu", OptionList)
        menu.clear_options()

        # 슬래시 제거 후 소문자로 비교
        search_term = filter_text.lstrip("/").lower()

        matches_found = 0
        for cmd, desc, cmd_id in self.commands:
            if not search_term or cmd.lstrip("/").startswith(search_term):
                menu.add_option(Option(f"{cmd:<10} [dim]{desc}[/dim]", id=cmd_id))
                matches_found += 1

        if matches_found > 0:
            menu.remove_class("hidden")  # hidden 클래스 제거
            menu.add_class("visible")
            self.visible = True
            menu.highlighted = 0
        else:
            menu.remove_class("visible")
            menu.add_class("hidden")  # hidden 클래스 추가
            self.visible = False

    def hide(self):
        """팔레트 숨기기"""
        menu = self.app.query_one("#command-menu", OptionList)
        menu.remove_class("visible")
        menu.add_class("hidden")  # hidden 클래스 추가
        self.visible = False
