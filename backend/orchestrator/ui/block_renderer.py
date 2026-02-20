"""
Block Renderer — Numbered Q&A block system for the CLI REPL.
Each query/response pair is stored as a Block and rendered as a rich Panel.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.table import Table
from rich import box


@dataclass
class Block:
    index: int
    query: str
    response: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


class BlockStore:
    """In-memory store for Q&A blocks."""

    def __init__(self):
        self._blocks: List[Block] = []

    def add(self, query: str, response: str, metadata: dict = None) -> Block:
        block = Block(
            index=len(self._blocks) + 1,
            query=query,
            response=response,
            metadata=metadata or {},
        )
        self._blocks.append(block)
        return block

    def get(self, index: int) -> Optional[Block]:
        if 1 <= index <= len(self._blocks):
            return self._blocks[index - 1]
        return None

    def all(self) -> List[Block]:
        return list(self._blocks)

    def count(self) -> int:
        return len(self._blocks)


class BlockRenderer:
    """Renders Block objects as rich Panels to the terminal."""

    def __init__(self, console: Console):
        self.console = console

    def render(self, block: Block) -> None:
        ts = block.timestamp.strftime("%H:%M")
        query_preview = block.query[:60] + ("…" if len(block.query) > 60 else "")
        title = f"[dim]#{block.index}[/dim]  [dim]{ts}[/dim]  {query_preview}"
        try:
            content = Markdown(block.response)
        except Exception:
            content = Text(block.response)
        self.console.print(
            Panel(
                content,
                title=title,
                title_align="left",
                border_style="dim",
                box=box.SIMPLE_HEAD,
                padding=(0, 1),
            )
        )

    def render_history_list(self, blocks: List[Block]) -> None:
        if not blocks:
            self.console.print("[dim]아직 대화가 없습니다.[/dim]")
            return
        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        t.add_column("No", style="cyan dim", width=4)
        t.add_column("시간", style="dim", width=6)
        t.add_column("질문")
        for b in blocks:
            query_preview = b.query[:60] + ("…" if len(b.query) > 60 else "")
            t.add_row(f"#{b.index}", b.timestamp.strftime("%H:%M"), query_preview)
        self.console.print(t)

    def render_block_ref(self, block: Block) -> None:
        """Re-render a specific block (used for @N references)."""
        self.console.print(f"\n[dim]블록 #{block.index} 참조:[/dim]")
        self.render(block)
