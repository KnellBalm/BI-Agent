"""AaC 스테이지 템플릿 패키지."""
from backend.aac.templates.ask import render as render_ask
from backend.aac.templates.look import render as render_look
from backend.aac.templates.investigate import render as render_investigate
from backend.aac.templates.voice import render as render_voice
from backend.aac.templates.evolve import render as render_evolve
from backend.aac.templates.quick import render as render_quick

__all__ = [
    "render_ask",
    "render_look",
    "render_investigate",
    "render_voice",
    "render_evolve",
    "render_quick",
]
