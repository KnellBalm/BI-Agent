"""
SchemaExplorerSidebar 위젯
메인 채팅 콘솔 좌측에 도킹되어 데이터베이스 스키마(테이블/컬럼)를 보여주는 인라인 사이드바.
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, Tree, Button, Static
from textual.binding import Binding

from backend.agents.data_source.metadata_scanner import MetadataScanner
from backend.agents.data_source.connection_manager import ConnectionManager as AgentConnectionManager

logger = logging.getLogger("tui")


class SchemaExplorerSidebar(Static):
    """
    메인 콘솔 좌측에 도킹되는 스키마 탐색기 사이드바.
    연결 성공 시 자동으로 표시되며, /explore 명령으로 토글 가능.
    """

    DEFAULT_CSS = """
    SchemaExplorerSidebar {
        width: 32;
        height: 100%;
        dock: left;
        background: $surface;
        border-right: thick $accent;
        display: none;
    }

    SchemaExplorerSidebar .sidebar-header {
        height: 3;
        padding: 1 1 0 1;
        color: $accent;
        text-style: bold;
    }

    SchemaExplorerSidebar .sidebar-conn-info {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }

    SchemaExplorerSidebar #schema-sidebar-tree {
        height: 1fr;
        padding: 0 1;
        background: transparent;
    }

    SchemaExplorerSidebar #sidebar-close-btn {
        dock: bottom;
        height: 1;
        width: 100%;
        min-width: 10;
        text-style: dim;
    }
    """

    def __init__(
        self,
        agent_conn_mgr: AgentConnectionManager,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.agent_conn_mgr = agent_conn_mgr
        self._connection_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Label("📂 스키마 탐색기", classes="sidebar-header")
        yield Label("[dim]연결 없음[/dim]", id="sidebar-conn-label", classes="sidebar-conn-info")
        yield Tree("Database", id="schema-sidebar-tree")
        yield Button("✕ 닫기 (Esc)", id="sidebar-close-btn", variant="default")

    @property
    def connection_id(self) -> Optional[str]:
        return self._connection_id

    def show_for_connection(self, connection_id: str) -> None:
        """지정된 연결의 스키마를 로드하고 사이드바를 표시합니다."""
        self._connection_id = connection_id
        self.display = True

        # 연결 정보 라벨 업데이트
        try:
            conn_label = self.query_one("#sidebar-conn-label", Label)
            conn_label.update(f"[cyan]{connection_id}[/cyan]")
        except Exception:
            pass

        # 스키마 비동기 로드
        asyncio.create_task(self._load_schema())

    def hide_sidebar(self) -> None:
        """사이드바를 숨깁니다."""
        self.display = False

    def toggle(self) -> None:
        """사이드바 가시성을 토글합니다."""
        if self.display:
            self.hide_sidebar()
        else:
            if self._connection_id:
                self.display = True
            else:
                self.app.notify("활성화된 연결이 없습니다. /connect 를 먼저 실행하세요.", severity="warning")

    async def _load_schema(self) -> None:
        """MetadataScanner를 사용하여 연결의 스키마를 로드합니다."""
        tree = self.query_one("#schema-sidebar-tree", Tree)
        tree.clear()
        tree.root.expand()

        # 로딩 표시
        loading_node = tree.root.add("📡 스키마 로딩 중...", expand=True)
        loading_node.add_leaf("잠시만 기다려 주세요...")

        try:
            conn_id = self._connection_id
            if not conn_id:
                raise ValueError("연결 ID가 설정되지 않았습니다.")

            # 블로킹 작업을 스레드 풀에서 실행
            def _scan():
                scanner = MetadataScanner(self.agent_conn_mgr)
                return scanner.scan_source(conn_id, deep_scan=False)

            loop = asyncio.get_event_loop()
            metadata = await loop.run_in_executor(None, _scan)

            # 로딩 표시 제거
            tree.root.remove_children()

            # 테이블 추가
            table_list = metadata.get("tables", [])
            tables_node = tree.root.add(f"📊 테이블 ({len(table_list)})", expand=True)

            if table_list:
                for table_info in table_list:
                    table_name = table_info.get("table_name", "unknown")
                    columns = table_info.get("columns", [])

                    if columns:
                        table_node = tables_node.add(f"📋 {table_name}")
                        for col in columns:
                            col_name = col.get("column_name", col.get("name", "?"))
                            col_type = col.get("data_type", col.get("type", "?"))
                            table_node.add_leaf(f"  {col_name} [dim]({col_type})[/dim]")
                    else:
                        tables_node.add_leaf(f"📋 {table_name}")

                self.app.notify(f"✓ {len(table_list)}개 테이블 로드 완료", severity="information")
            else:
                tables_node.add_leaf("  (테이블 없음)")
                self.app.notify("데이터베이스에서 테이블을 찾지 못했습니다.", severity="warning")

            logger.info(f"Schema sidebar loaded {len(table_list)} tables for {conn_id}")

        except Exception as e:
            logger.error(f"Schema sidebar load failed: {e}", exc_info=True)
            tree.root.remove_children()
            error_node = tree.root.add("❌ 스키마 로드 실패", expand=True)
            error_node.add_leaf(f"  {str(e)}")
            self.app.notify(f"스키마 로드 실패: {str(e)}", severity="error", timeout=10)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "sidebar-close-btn":
            self.hide_sidebar()
