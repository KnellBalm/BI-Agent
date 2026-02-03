import logging
from typing import Any, Optional

from textual.widgets import Input, OptionList
from textual.app import App

from backend.orchestrator.handlers.protocols import HandlerContext, InputHandlerProtocol

logger = logging.getLogger("tui")

class InputHandler(InputHandlerProtocol):
    """
    키보드 입력 처리 및 자동완성 로직을 담당하는 핸들러
    """
    def __init__(self, context: HandlerContext, command_palette: Any, command_history: Any):
        self.context = context
        self.app = context.app
        self.palette = command_palette
        self.history = command_history
        self.command_list = command_palette.commands

    async def handle_key(self, event: Any) -> bool:
        """Handle global keys for menu navigation, Tab autocomplete, and history navigation."""
        user_input = self.context.query_one("#user-input", Input)
        menu = self.context.query_one("#command-menu", OptionList)

        # 1. '/' 키 처리 (포커스 이동)
        if event.key in ("/", "slash", "forward_slash"):
            if not user_input.has_focus:
                if hasattr(self.app, "action_focus_input_with_slash"):
                    self.app.action_focus_input_with_slash()
                    return True

        # 2. 히스토리 내비게이션 (Up/Down)
        if user_input.has_focus and not self.palette.visible:
            if event.key == "up":
                prev_cmd = self.history.get_previous()
                if prev_cmd is not None:
                    user_input.value = prev_cmd
                    user_input.cursor_position = len(user_input.value)
                    return True
            elif event.key == "down":
                next_cmd = self.history.get_next()
                if next_cmd is not None:
                    user_input.value = next_cmd
                    user_input.cursor_position = len(user_input.value)
                    return True

        # 3. 자동완성 (Tab)
        if event.key == "tab" and user_input.has_focus:
            return self._handle_tab_completion(user_input, menu)

        # 4. 팔레트 제어 (Palette Visible 모드)
        if self.palette.visible and user_input.has_focus:
            if event.key == "escape":
                self.palette.hide()
                return True
            elif event.key == "up":
                if menu.highlighted is not None and menu.highlighted > 0:
                    menu.highlighted -= 1
                return True
            elif event.key == "down":
                if menu.highlighted is not None and menu.highlighted < menu.option_count - 1:
                    menu.highlighted += 1
                return True
            elif event.key == "enter":
                if menu.highlighted is not None:
                    option = menu.get_option_at_index(menu.highlighted)
                    if option and option.id:
                        self._execute_palette_command(option.id, user_input)
                        return True

        return False

    def _handle_tab_completion(self, user_input: Input, menu: OptionList) -> bool:
        current_text = user_input.value.strip()

        # 팔레트 항목 완성
        if self.palette.visible:
            if menu.highlighted is not None:
                opt = menu.get_option_at_index(menu.highlighted)
                matching_cmd = next((c[0] for c in self.command_list if c[2] == opt.id), None)
                if matching_cmd:
                    user_input.value = matching_cmd
                    user_input.cursor_position = len(user_input.value)
                    self.palette.hide()
                    return True

        # 슬래시 명령어 자동 완성
        if current_text.startswith("/") or (current_text and len(current_text) >= 1):
            raw_prefix = current_text.lstrip("/")
            matches = [c[0] for c in self.command_list if c[0].lstrip("/").startswith(raw_prefix)]

            if len(matches) == 1:
                user_input.value = matches[0]
                user_input.cursor_position = len(user_input.value)
                return True
            elif len(matches) > 1:
                common = matches[0].lstrip("/")
                for m in matches[1:]:
                    while not m.lstrip("/").startswith(common):
                        common = common[:-1]
                if len(common) > len(raw_prefix):
                    user_input.value = "/" + common
                    user_input.cursor_position = len(user_input.value)
                    return True
        
        # 한국어 BI 문구 및 히스토리 자동 완성
        suggestions = self.history.get_suggestions(current_text)
        if len(suggestions) == 1:
            user_input.value = suggestions[0]
            user_input.cursor_position = len(user_input.value)
            return True
        elif len(suggestions) > 1:
            # Common prefix logic...
            pass
            
        return False

    def _execute_palette_command(self, command_id: str, user_input: Input):
        cmd = "/" + command_id.replace("cmd_", "")
        user_input.value = ""
        self.palette.hide()
        import asyncio
        asyncio.create_task(self.context.handle_command(cmd))
