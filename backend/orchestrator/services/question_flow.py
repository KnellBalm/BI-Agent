"""
QuestionFlowEngine - Inline CLI question flow engine.

Replaces modal screens with conversational question/answer flows
rendered directly in the chat log as MessageBubbles.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable

from textual.containers import VerticalScroll

logger = logging.getLogger(__name__)


@dataclass
class FlowResult:
    """Result returned by a flow's on_complete callback."""

    success: bool
    message: str
    retry_from_question: str | None = None


@dataclass
class Question:
    """Definition of a single question in a flow."""

    id: str
    prompt: str | Callable[[dict], str]  # Rich-formatted text or callable
    input_type: str  # "choice" | "text" | "password" | "confirm"
    choices: list[tuple[str, str]] = field(default_factory=list)  # [(value, label), ...]
    default: str | Callable[[dict], str] | None = None  # Static or dynamic default
    validator: Callable[[str], str | None] | None = None  # Returns error message or None
    next_question: str | Callable[[dict], str | None] | None = None  # Next question ID or function
    transform: Callable[[str], Any] | None = None  # Transform before storing


@dataclass
class FlowDefinition:
    """Complete definition of a question flow."""

    flow_id: str
    title: str
    questions: dict[str, Question]
    first_question: str
    on_complete: Callable[[dict], Awaitable[FlowResult]]  # Async callback


# Passthrough commands that are NOT blocked during an active flow
_PASSTHROUGH_COMMANDS = frozenset({"/help", "/quit", "/exit"})


class QuestionFlowEngine:
    """Engine that drives inline question/answer flows in the chat log.

    Usage::

        engine = QuestionFlowEngine(chat_log)
        engine.start_flow(my_flow_definition)
        # Then, for each user input while engine.is_active():
        #   consumed = await engine.handle_input(text)
    """

    def __init__(self, chat_log: VerticalScroll | None = None, app: Any | None = None) -> None:
        self.chat_log: VerticalScroll | None = chat_log
        self.app: Any | None = app
        self.active_flow: FlowDefinition | None = None
        self.current_question_id: str | None = None
        self.answers: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_flow(self, flow: FlowDefinition) -> None:
        """Begin a new question flow.

        Resets internal state, renders the flow title, and displays
        the first question.
        """
        self.active_flow = flow
        self.current_question_id = flow.first_question
        self.answers = {}

        # Update input placeholder
        if self.app:
            try:
                input_widget = self.app.query_one("#user-input")
                input_widget.placeholder = "Answer question above (/cancel to abort)"
            except Exception:
                pass

        # Render title banner
        self._mount_bubble(
            "system",
            f"[bold cyan]━━━ {flow.title} ━━━[/bold cyan]\n"
            f"[dim]Type /cancel to abort.[/dim]",
        )

        first_q = flow.questions.get(flow.first_question)
        if first_q is None:
            logger.error(
                "Flow '%s' references unknown first_question '%s'",
                flow.flow_id,
                flow.first_question,
            )
            self._reset()
            return
        self._render_question(first_q)

    async def handle_input(self, text: str) -> bool:
        """Process user input during an active flow.

        Returns ``True`` if the input was consumed by the flow engine
        (callers should NOT process it further), or ``False`` if it
        should be passed through to normal command handling.
        """
        if not self.is_active():
            return False

        stripped = text.strip()

        # --- /cancel: abort flow ---
        if stripped.lower() == "/cancel":
            self.cancel()
            return True

        # --- passthrough commands ---
        cmd_token = stripped.split()[0].lower() if stripped else ""
        if cmd_token in _PASSTHROUGH_COMMANDS:
            return False

        # --- block other slash-commands ---
        if stripped.startswith("/"):
            self._mount_bubble(
                "system",
                "[yellow]Complete or cancel the current flow first.[/yellow]",
            )
            return True

        # --- normal input processing ---
        assert self.active_flow is not None
        assert self.current_question_id is not None

        question = self.active_flow.questions[self.current_question_id]

        # Resolve actual value from input
        value = self._resolve_input(stripped, question)
        if value is None:
            # _resolve_input already rendered an error
            return True

        # Validate
        if question.validator is not None:
            error = question.validator(value)
            if error is not None:
                self._mount_bubble("system", f"[red]{error}[/red]")
                self._render_question(question)
                return True

        # Render the user's answer
        self._render_answer(value, is_password=(question.input_type == "password"))

        # Transform before storing
        stored_value: Any = value
        if question.transform is not None:
            try:
                stored_value = question.transform(value)
            except Exception as exc:
                self._mount_bubble(
                    "system",
                    f"[red]Invalid input: {exc}[/red]",
                )
                self._render_question(question)
                return True

        self.answers[question.id] = stored_value

        # Determine next question
        next_id = self._resolve_next(question)

        if next_id is not None:
            next_q = self.active_flow.questions.get(next_id)
            if next_q is None:
                logger.error(
                    "Flow '%s' references unknown question '%s'",
                    self.active_flow.flow_id,
                    next_id,
                )
                self._mount_bubble(
                    "system",
                    "[red]Internal error: unknown next question. Flow aborted.[/red]",
                )
                self._reset()
                return True
            self.current_question_id = next_id
            self._render_question(next_q)
            return True

        # Flow complete — invoke on_complete callback
        await self._finish_flow()
        return True

    def cancel(self) -> None:
        """Abort the current flow."""
        if self.active_flow is not None:
            flow_title = self.active_flow.title
            self._reset()
            self._mount_bubble(
                "system",
                f"[yellow]{flow_title} cancelled.[/yellow]",
            )
            # Restore placeholder
            if self.app:
                try:
                    input_widget = self.app.query_one("#user-input")
                    input_widget.placeholder = "질문을 입력하거나 '/'로 명령어를 시작하세요..."
                except Exception:
                    pass

    def is_active(self) -> bool:
        """Return True if a flow is currently in progress."""
        return self.active_flow is not None and self.current_question_id is not None

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render_question(self, question: Question) -> None:
        """Render a question as a MessageBubble in the chat log."""
        # Resolve callable prompt (similar to _resolve_default pattern at line 282)
        prompt_text = question.prompt(self.answers) if callable(question.prompt) else question.prompt
        lines: list[str] = [f"[bold]{prompt_text}[/bold]"]

        if question.input_type == "choice" and question.choices:
            for idx, (value, label) in enumerate(question.choices, 1):
                lines.append(f"  [cyan][{idx}][/cyan] {label}")

        if question.input_type == "confirm":
            lines.append("[dim](y/n)[/dim]")

        default = self._resolve_default(question)
        if default is not None:
            if question.input_type == "password":
                lines.append("[dim]Default: ********[/dim]")
            else:
                lines.append(f"[dim]Default: {default}[/dim]")

        self._mount_bubble("agent", "\n".join(lines))

    def _render_answer(self, text: str, is_password: bool) -> None:
        """Render the user's answer (masking passwords)."""
        display = "********" if is_password else text
        self._mount_bubble("user", display)

    def _mount_bubble(self, role: str, content: str) -> None:
        """Mount a MessageBubble into the chat log (no-op if chat_log is None)."""
        if self.chat_log is None:
            return
        try:
            from backend.orchestrator.ui.components.message_components import (
                MessageBubble,
            )

            bubble = MessageBubble(role=role, content=content, timestamp=datetime.now())
            self.chat_log.mount(bubble)
            bubble.scroll_visible()
        except Exception:
            logger.debug("Failed to mount bubble in chat log", exc_info=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_default(self, question: Question) -> str | None:
        """Resolve a question's default value (static or dynamic)."""
        if question.default is None:
            return None
        if callable(question.default):
            try:
                return question.default(self.answers)
            except Exception:
                logger.debug("Dynamic default failed", exc_info=True)
                return None
        return question.default

    def _resolve_input(self, raw: str, question: Question) -> str | None:
        """Resolve and normalize user input for a given question.

        Returns the resolved value string, or ``None`` if the input
        was invalid (an error bubble is rendered in that case).
        """
        value = raw

        # Use default on empty input
        if not value:
            default = self._resolve_default(question)
            if default is not None:
                value = default
            else:
                self._mount_bubble("system", "[red]Input required.[/red]")
                self._render_question(question)
                return None

        # Choice resolution
        if question.input_type == "choice" and question.choices:
            # Accept numeric selection
            if value.isdigit():
                idx = int(value) - 1
                if 0 <= idx < len(question.choices):
                    return question.choices[idx][0]
                self._mount_bubble(
                    "system",
                    f"[red]Invalid choice. Enter 1-{len(question.choices)}.[/red]",
                )
                self._render_question(question)
                return None

            # Accept value string (case-insensitive)
            valid_values = {v.lower(): v for v, _ in question.choices}
            if value.lower() in valid_values:
                return valid_values[value.lower()]

            self._mount_bubble(
                "system",
                "[red]Invalid choice. Enter a number or value.[/red]",
            )
            self._render_question(question)
            return None

        # Confirm normalization
        if question.input_type == "confirm":
            lower = value.lower()
            if lower in ("y", "yes", "true", "1"):
                return "y"
            if lower in ("n", "no", "false", "0"):
                return "n"
            self._mount_bubble("system", "[red]Please enter y or n.[/red]")
            self._render_question(question)
            return None

        return value

    def _resolve_next(self, question: Question) -> str | None:
        """Resolve the next question ID (static, dynamic, or None for end)."""
        if question.next_question is None:
            return None
        if callable(question.next_question):
            try:
                return question.next_question(self.answers)
            except Exception:
                logger.debug("Dynamic next_question failed", exc_info=True)
                return None
        return question.next_question

    async def _finish_flow(self) -> None:
        """Invoke the on_complete callback and handle the result."""
        assert self.active_flow is not None
        flow = self.active_flow
        answers = dict(self.answers)

        try:
            result = await flow.on_complete(answers)
        except Exception as exc:
            logger.error("Flow on_complete raised: %s", exc, exc_info=True)
            self._mount_bubble(
                "system",
                f"[red]Error: {exc}[/red]",
            )
            self._reset()
            return

        if result.success:
            self._mount_bubble("system", f"[green]{result.message}[/green]")
            self._reset()
        elif result.retry_from_question is not None:
            # Resume from a specific question
            self._mount_bubble("system", f"[yellow]{result.message}[/yellow]")
            retry_q = flow.questions.get(result.retry_from_question)
            if retry_q is not None:
                self.current_question_id = result.retry_from_question
                self._render_question(retry_q)
            else:
                logger.error(
                    "retry_from_question '%s' not found in flow '%s'",
                    result.retry_from_question,
                    flow.flow_id,
                )
                self._reset()
        else:
            # Failure without retry
            self._mount_bubble("system", f"[red]{result.message}[/red]")
            self._reset()

    def _reset(self) -> None:
        """Reset engine state after flow completion or cancellation."""
        self.active_flow = None
        self.current_question_id = None
        self.answers = {}
        # Restore placeholder
        if self.app:
            try:
                input_widget = self.app.query_one("#user-input")
                input_widget.placeholder = "질문을 입력하거나 '/'로 명령어를 시작하세요..."
            except Exception:
                pass
