"""
VimEngine Module
Provides Vim-style modal editing functionality for Textual widgets.
Inspired by sqlit interaction model.
"""

from enum import Enum, auto
from typing import Optional, List, Callable
from textual.message import Message
from textual.widgets import TextArea

class VimMode(Enum):
    NORMAL = auto()
    INSERT = auto()
    VISUAL = auto()  # Future expansion

class VimEngine:
    """
    Mixin-like helper to add Vim behavior to a widget.
    Usage:
        class VimTextArea(TextArea, VimEngine):
            ...
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vim_mode = VimMode.NORMAL
        self.leader_key: Optional[str] = None

    class ModeChanged(Message):
        """Sent when the vim mode changes."""
        def __init__(self, mode: VimMode) -> None:
            super().__init__()
            self.mode = mode

    def set_vim_mode(self, mode: VimMode):
        """Switch the current editing mode."""
        if self.vim_mode != mode:
            self.vim_mode = mode
            self.post_message(self.ModeChanged(mode))
            self._update_vim_style()

    def _update_vim_style(self):
        """Update widget classes for CSS styling."""
        if self.vim_mode == VimMode.NORMAL:
            self.remove_class("vim-mode-insert")
            self.add_class("vim-mode-normal")
            self.read_only = True
            self.show_cursor = True
        else:
            self.remove_class("vim-mode-normal")
            self.add_class("vim-mode-insert")
            self.read_only = False
            self.show_cursor = True

    async def handle_vim_key(self, key: str) -> bool:
        """
        Handle a key press based on current mode.
        Returns True if the key was handled.
        """
        if self.vim_mode == VimMode.NORMAL:
            return await self._handle_normal_mode(key)
        else:
            return await self._handle_insert_mode(key)

    async def _handle_normal_mode(self, key: str) -> bool:
        # Basic movements
        if key == "h":
            self.move_cursor_relative(columns=-1)
        elif key == "j":
            self.move_cursor_relative(lines=1)
        elif key == "k":
            self.move_cursor_relative(lines=-1)
        elif key == "l":
            self.move_cursor_relative(columns=1)
        
        # Mode transitions
        elif key == "i":
            self.set_vim_mode(VimMode.INSERT)
        elif key == "a":
            self.move_cursor_relative(columns=1)
            self.set_vim_mode(VimMode.INSERT)
        elif key == "A":
            self.move_cursor_to_line_end()
            self.set_vim_mode(VimMode.INSERT)
        elif key == "o":
            self.insert_text("\n")
            self.set_vim_mode(VimMode.INSERT)
        
        # Actions
        elif key == "x":
            self.delete_range(self.cursor_location, (self.cursor_location[0], self.cursor_location[1] + 1))
        elif key == "u":
            self.undo()
        elif key == "ctrl+r":
            self.redo()
            
        else:
            return False  # Key not handled in normal mode
            
        return True

    async def _handle_insert_mode(self, key: str) -> bool:
        if key == "escape":
            self.set_vim_mode(VimMode.NORMAL)
            return True
        return False  # Let standard input handle it
