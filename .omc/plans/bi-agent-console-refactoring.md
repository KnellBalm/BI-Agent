# BI-Agent Console Refactoring Plan

## Context

### Original Request
Refactor `backend/orchestrator/bi_agent_console.py` (1883 lines) to improve stability and extensibility by separating mixed concerns.

### Interview Summary
- The file contains the main TUI application with multiple modal screens, command handling, sidebar management, and business logic all mixed together
- The codebase already has a `screens/` directory with properly extracted screens (e.g., `TableSelectionScreen`, `VisualAnalysisScreen`)
- Existing patterns show clear separation: screens in dedicated files, CSS embedded in classes, proper logging setup

### Research Findings
1. **Existing Pattern**: The project already has `backend/orchestrator/screens/` directory with properly structured screen files
2. **Component Pattern**: `message_components.py` shows how UI components are extracted
3. **Manager Pattern**: `context_manager.py` and `command_history.py` show singleton manager patterns
4. **Related Files**: 21 files in `backend/orchestrator/` - several could share extracted logic

---

## Work Objectives

### Core Objective
Transform the monolithic 1883-line `bi_agent_console.py` into a modular, maintainable architecture while preserving 100% of existing functionality.

### Deliverables
1. **AuthScreen** extracted to `screens/auth_screen.py` (~190 lines)
2. **ConnectionScreen** extracted to `screens/connection_screen.py` (~500 lines)
3. **ProjectScreen** extracted to `screens/project_screen.py` (~70 lines)
4. **CommandHandler** extracted to `handlers/command_handler.py` (~200 lines) with Protocol-based design
5. **SidebarManager** extracted to `components/sidebar_manager.py` (~150 lines)
6. **Refactored BI_AgentConsole** (~400 lines, down from ~900 lines of main app logic)
7. All existing functionality verified working (including F1 bug fix)

### Definition of Done
- [ ] Critical bug fixed (F1 help / `_run_help` issue)
- [ ] All 3 modal screens extracted and functional
- [ ] Command routing delegated to CommandHandler using Mediator pattern
- [ ] Sidebar logic delegated to SidebarManager
- [ ] Main console file under 500 lines
- [ ] No regression in existing functionality
- [ ] All existing tests pass (if any)
- [ ] Imports updated across codebase
- [ ] No circular dependencies

---

## Guardrails

### Must Have
- Preserve ALL existing keyboard bindings (q, /, escape, ctrl+l, F1)
- Preserve ALL slash commands (/intent, /analyze, /explore, /connect, /project, /login, /report, /help, /errors, /quit, /exit)
- Preserve sidebar update mechanism (10-second interval)
- Preserve command history functionality
- Preserve command palette auto-complete behavior
- Maintain Korean and English mixed UI text
- Keep error logging to `diagnostic_logger` and `textual_errors.log`
- Follow existing code style (Korean docstrings, type hints)

### Must NOT Have
- Breaking changes to public interfaces
- New dependencies
- Changes to existing screen files in `screens/`
- Modifications to `context_manager.py`, `command_history.py`, or other manager files
- UI visual changes (CSS must remain identical)

---

## Identified Concerns in Current File

### 1. Critical Bug (MUST FIX FIRST)
| Bug | Location | Issue | Fix |
|-----|----------|-------|-----|
| Missing `_run_help` method | Line 1858-1860 | `action_show_help()` calls `await self._run_help()` which does not exist | Change to `await self.handle_command("/help")` |

### 2. Modal Screens (Lines 38-861)
| Screen | Lines | Responsibility |
|--------|-------|----------------|
| `AuthScreen` | 38-293 | LLM provider authentication modal |
| `ConnectionScreen` | 295-795 | Data source connection management |
| `ProjectScreen` | 797-861 | Project selection/creation |

### 3. Main Application Class (Lines 863-1860)
| Section | Lines | Responsibility |
|---------|-------|----------------|
| CSS Styles | 868-967 | Application-wide styling |
| Key Bindings | 969-975 | Global keyboard shortcuts |
| Command List | 977-989 | Slash command definitions |
| Initialization | 992-1064 | App and orchestrator setup |
| UI Composition | 1066-1102 | Widget tree structure |
| Lifecycle Hooks | 1104-1154 | Mount, sidebar init |
| Sidebar Updates | 1156-1267 | Status panel refresh logic |
| HUD Updates | 1273-1295 | HUD statusline refresh |
| Command Menu | 1297-1318 | Palette filtering |
| Input Handling | 1319-1545 | Key events, history, autocomplete |
| Command Routing | 1547-1609 | Slash command dispatch |
| Query Processing | 1611-1633 | Natural language handling |
| Worker Tasks | 1635-1800 | Async explore, scan, analyze |
| Actions | 1802-1860 | Clear, project switch, quit |

### 4. Entry Point (Lines 1862-1883)
Standalone `run_app()` function

---

## Proposed Architecture

```
backend/orchestrator/
|-- bi_agent_console.py          # Main App class (~400 lines)
|-- handlers/
|   |-- __init__.py
|   |-- protocols.py             # NEW: Handler and Context Protocols
|   |-- command_handler.py       # Slash command routing (~200 lines)
|   |-- input_handler.py         # Key events, history, autocomplete (~150 lines)
|-- components/
|   |-- __init__.py
|   |-- sidebar_manager.py       # Sidebar update logic (~150 lines)
|   |-- command_palette.py       # Command menu logic (~80 lines)
|-- screens/
|   |-- __init__.py              # Update exports
|   |-- auth_screen.py           # NEW: AuthScreen (~190 lines)
|   |-- connection_screen.py     # NEW: ConnectionScreen (~500 lines)
|   |-- project_screen.py        # NEW: ProjectScreen (~70 lines)
|   |-- (existing screens...)
```

---

## Protocol-Based Design (Architect Recommendation)

### Handler Protocol (handlers/protocols.py)

```python
from typing import Protocol, List, Optional, Any, Callable, Awaitable

class HandlerContext(Protocol):
    """Protocol defining app capabilities available to handlers."""

    # UI Access
    def query_one(self, selector: str, expect_type: type = None) -> Any: ...
    def push_screen(self, screen: Any) -> None: ...
    def run_worker(self, coro: Awaitable) -> None: ...

    # State Access
    @property
    def conn_mgr(self) -> Any: ...
    @property
    def orchestrator(self) -> Any: ...
    @property
    def context_manager(self) -> Any: ...

    # Callbacks (worker methods stay in App)
    def get_worker_callback(self, name: str) -> Callable: ...

class CommandHandler(Protocol):
    """Protocol for command handlers."""

    async def handle(self, cmd_text: str) -> None: ...
    def can_handle(self, cmd: str) -> bool: ...

class InputHandler(Protocol):
    """Protocol for input handlers."""

    async def on_key(self, event: Any) -> None: ...
    def on_input_changed(self, event: Any) -> None: ...
```

### Mediator Pattern Implementation

The `CommandHandler` acts as a **Mediator** between:
- Command input (the `/command` strings)
- Worker methods (in the App class for UI access)
- External services (conn_mgr, orchestrator)

```python
class CommandHandlerImpl:
    """Concrete implementation using Mediator pattern."""

    def __init__(self, context: HandlerContext):
        self._context = context
        self._command_map = {
            "/intent": self._handle_intent,
            "/analyze": self._handle_analyze,
            "/explore": self._handle_explore,
            "/connect": self._handle_connect,
            "/project": self._handle_project,
            "/login": self._handle_login,
            "/report": self._handle_report,
            "/help": self._handle_help,
            "/errors": self._handle_errors,
            "/quit": self._handle_quit,
            "/exit": self._handle_quit,  # Alias
        }

    async def handle(self, cmd_text: str) -> None:
        parts = cmd_text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handler = self._command_map.get(cmd)
        if handler:
            await handler(args)
        else:
            self._show_error(f"알 수 없는 명령어입니다: {cmd}")
```

---

## Task Flow and Dependencies

```
Phase 0: Critical Bug Fix (BLOCKING)
  |-- Task 0.1: Fix missing _run_help method

Phase 1: Extract Modal Screens (Independent, can parallelize)
  |-- Task 1.1: Extract AuthScreen
  |-- Task 1.2: Extract ConnectionScreen
  |-- Task 1.3: Extract ProjectScreen

Phase 2: Extract Support Components
  |-- Task 2.1: Extract SidebarManager
  |-- Task 2.2: Extract CommandPalette (depends on nothing)

Phase 3: Extract Handlers with Protocol Pattern
  |-- Task 3.0: Create Handler Protocols (NEW)
  |-- Task 3.1: Extract CommandHandler with Mediator pattern (depends on 3.0, Phase 1)
  |-- Task 3.2: Extract InputHandler (depends on 3.0, 2.2)

Phase 4: Refactor Main App
  |-- Task 4.1: Update BI_AgentConsole to use extracted modules
  |-- Task 4.2: Update imports in dependent files

Phase 5: Verification
  |-- Task 5.1: Run application and verify all features
  |-- Task 5.2: Update any affected imports in codebase
```

---

## Detailed TODOs

### Task 0.1: Fix Critical F1 Help Bug (BLOCKING)
**File:** `backend/orchestrator/bi_agent_console.py`

**Issue:** Line 1858-1860: `action_show_help()` calls `await self._run_help()` but `_run_help` method does not exist. This causes `AttributeError` when pressing F1.

**Current Code (Line 1858-1860):**
```python
async def action_show_help(self) -> None:
    """도움말 표시"""
    await self._run_help()
```

**Fixed Code:**
```python
async def action_show_help(self) -> None:
    """도움말 표시"""
    await self.handle_command("/help")
```

**Acceptance Criteria:**
- [ ] F1 key press no longer raises AttributeError
- [ ] F1 displays help message in chat log (same as `/help` command)
- [ ] Verified by manual testing

---

### Task 0.2: Fix AuthScreen Sidebar Bug (CRITICAL)
**File:** `backend/orchestrator/bi_agent_console.py`

**Issue:** Line 286 in `AuthScreen._save_api_key()` calls `await self._update_sidebar()` but `AuthScreen` has no such method. This causes an `AttributeError` when saving API keys.

**Fix:**
```python
# Line 286: Change from
await self._update_sidebar()
# To
await self.app._update_sidebar()
```

**Acceptance Criteria:**
- [ ] Saving API key no longer raises AttributeError
- [ ] Sidebar updates after successful auth

---

### Task 1.1: Extract AuthScreen
**File:** `backend/orchestrator/screens/auth_screen.py`

**Source Lines:** 38-293 from `bi_agent_console.py`

**Steps:**
1. Create `auth_screen.py` with proper imports
2. Copy `AuthScreen` class (lines 38-293)
3. Add required imports: `json`, `logging`, `textual.*`, `auth_manager`, `quota_manager`, `path_manager`, `context_manager`
4. Initialize logger with `setup_logger("auth_screen", "auth_screen.log")`
5. Update `screens/__init__.py` to export `AuthScreen`
6. Update `bi_agent_console.py` to import from `screens.auth_screen`

**Acceptance Criteria:**
- [ ] `/login` command opens AuthScreen
- [ ] Provider selection works (keyboard shortcuts 1,2,3)
- [ ] API key save and validation works
- [ ] ESC dismisses screen
- [ ] Journey progress updates correctly

---

### Task 1.2: Extract ConnectionScreen
**File:** `backend/orchestrator/screens/connection_screen.py`

**Source Lines:** 295-795 from `bi_agent_console.py`

**Steps:**
1. Create `connection_screen.py` with proper imports
2. Copy `ConnectionScreen` class (lines 295-795)
3. Add required imports: `json`, `logging`, `textual.*`
4. Initialize logger with `setup_logger("connection_screen", "connection_screen.log")`
5. Note: This screen accesses `self.app.conn_mgr` - keep this pattern
6. Update `screens/__init__.py` to export `ConnectionScreen`
7. Update `bi_agent_console.py` to import from `screens.connection_screen`

**Acceptance Criteria:**
- [ ] `/connect` command opens ConnectionScreen
- [ ] Existing connections listed
- [ ] New connection creation works (all types: sqlite, excel, postgres, mysql)
- [ ] SSH tunnel configuration works
- [ ] Edit/Delete existing connections works
- [ ] Keyboard shortcuts (C, E, D, Tab, Escape) work
- [ ] Connection callback triggers scan

---

### Task 1.3: Extract ProjectScreen
**File:** `backend/orchestrator/screens/project_screen.py`

**Source Lines:** 797-861 from `bi_agent_console.py`

**Steps:**
1. Create `project_screen.py` with proper imports
2. Copy `ProjectScreen` class (lines 797-861)
3. Add required imports: `textual.*`, `path_manager`
4. Initialize logger
5. Update `screens/__init__.py` to export `ProjectScreen`
6. Update `bi_agent_console.py` to import from `screens.project_screen`

**Acceptance Criteria:**
- [ ] `/project` command opens ProjectScreen
- [ ] Existing projects listed
- [ ] Current project highlighted
- [ ] New project creation works
- [ ] Project switch updates sidebar

---

### Task 1.4: Update screens/__init__.py Exports
**File:** `backend/orchestrator/screens/__init__.py`

**Current Content:**
```python
"""
Textual modal screens for BI-Agent interactive workflows
"""

from .table_selection_screen import TableSelectionScreen

__all__ = ["TableSelectionScreen"]
```

**Updated Content:**
```python
"""
Textual modal screens for BI-Agent interactive workflows
"""

from .table_selection_screen import TableSelectionScreen
from .auth_screen import AuthScreen
from .connection_screen import ConnectionScreen
from .project_screen import ProjectScreen

__all__ = [
    "TableSelectionScreen",
    "AuthScreen",
    "ConnectionScreen",
    "ProjectScreen",
]
```

**Acceptance Criteria:**
- [ ] All new screens importable via `from backend.orchestrator.screens import AuthScreen`
- [ ] No import errors

---

### Task 2.1: Extract SidebarManager
**File:** `backend/orchestrator/components/sidebar_manager.py`

**Source Lines:** 1156-1267 from `bi_agent_console.py`

**Steps:**
1. Create `components/` directory and `__init__.py`
2. Create `sidebar_manager.py`
3. Create `SidebarManager` class with:
   - `__init__(self, app: App)` - stores reference to app
   - `async update(self)` - main update logic (from `_update_sidebar`)
   - `_update_project_status(self)`
   - `_update_auth_status(self)`
   - `_update_quota_status(self)`
   - `_update_context_status(self)`
   - `_update_journey_progress(self)`
   - `_update_connection_status(self)`
   - `_update_recommendations(self)`
4. Extract sidebar update logic from `_update_sidebar` method (lines 1156-1267)
5. Update `bi_agent_console.py` to use `SidebarManager`

**Acceptance Criteria:**
- [ ] Sidebar updates every 10 seconds
- [ ] All sections update correctly (Project, Auth, Quota, Context, Journey, Sources, Recommendations)
- [ ] Journey progress visualization works
- [ ] Quota bars render correctly

---

### Task 2.2: Extract CommandPalette
**File:** `backend/orchestrator/components/command_palette.py`

**Source Lines:** 1297-1318, parts of 1483-1517 from `bi_agent_console.py`

**Steps:**
1. Create `command_palette.py`
2. Create `CommandPalette` class (wrapper around OptionList with filtering logic)
3. Move `_update_command_menu` logic
4. Move palette visibility state management
5. Keep command list definition in main app or move to constants

**Acceptance Criteria:**
- [ ] Typing `/` opens command palette
- [ ] Real-time filtering as user types
- [ ] Arrow keys navigate options
- [ ] Enter/click selects command
- [ ] Escape closes palette

---

### Task 3.0: Create Handler Protocols (NEW)
**File:** `backend/orchestrator/handlers/protocols.py`

**Steps:**
1. Create `handlers/` directory
2. Create `protocols.py` with Protocol definitions

**Full Content:**
```python
"""
Protocols for handler components using Python's structural typing.
Enables loose coupling between handlers and the App class.
"""
from typing import Protocol, Any, Callable, Awaitable, Optional

class HandlerContext(Protocol):
    """
    Protocol defining the app capabilities available to handlers.
    This enables handlers to work with any object that provides these methods,
    facilitating testing and loose coupling.
    """

    # UI Access
    def query_one(self, selector: str, expect_type: type = None) -> Any:
        """Query a single widget by selector."""
        ...

    def push_screen(self, screen: Any) -> None:
        """Push a modal screen."""
        ...

    def run_worker(self, coro: Awaitable) -> None:
        """Run an async coroutine as a background worker."""
        ...

    # State Access
    @property
    def conn_mgr(self) -> Any:
        """Connection manager instance."""
        ...

    @property
    def orchestrator(self) -> Optional[Any]:
        """Orchestrator instance (may be None before init)."""
        ...

    @property
    def context_manager(self) -> Any:
        """Context manager singleton."""
        ...

    # Worker Callbacks (for operations needing UI access)
    async def run_analysis(self, query: str) -> None:
        """Execute analysis workflow."""
        ...

    async def run_explore(self, target: Optional[str] = None) -> None:
        """Execute explore workflow."""
        ...

    def show_error_viewer(self) -> None:
        """Show the error viewer screen."""
        ...

class CommandHandlerProtocol(Protocol):
    """Protocol for command handlers."""

    async def handle(self, cmd_text: str) -> None:
        """Handle a slash command."""
        ...

    def can_handle(self, cmd: str) -> bool:
        """Check if handler can process this command."""
        ...

class InputHandlerProtocol(Protocol):
    """Protocol for input event handlers."""

    async def on_key(self, event: Any) -> None:
        """Handle key press events."""
        ...

    def on_input_changed(self, event: Any) -> None:
        """Handle input value changes."""
        ...
```

**Create handlers/__init__.py:**
```python
"""
Handler components for BI-Agent console.
"""
from .protocols import HandlerContext, CommandHandlerProtocol, InputHandlerProtocol
from .command_handler import CommandHandler
from .input_handler import InputHandler

__all__ = [
    "HandlerContext",
    "CommandHandlerProtocol",
    "InputHandlerProtocol",
    "CommandHandler",
    "InputHandler",
]
```

**Acceptance Criteria:**
- [ ] Protocols importable without errors
- [ ] Type checker validates protocol usage

---

### Task 3.1: Extract CommandHandler with Mediator Pattern
**File:** `backend/orchestrator/handlers/command_handler.py`

**Source Lines:** 1547-1609, 1755-1800 from `bi_agent_console.py`

**Steps:**
1. Create `command_handler.py`
2. Implement `CommandHandler` class with Mediator pattern:
   - `__init__(self, context: HandlerContext)` - stores context reference
   - `async handle(self, cmd_text: str)` - main routing via command map
   - `def can_handle(self, cmd: str) -> bool` - check if command is known
   - Individual handlers for each command

**Full Implementation:**
```python
"""
Command handler using Mediator pattern.
Routes slash commands to appropriate handlers while keeping
worker methods in the App class (they need UI access).
"""
from typing import Optional, Callable, Awaitable, Dict
import logging

from .protocols import HandlerContext

logger = logging.getLogger("command_handler")

class CommandHandler:
    """
    Mediator for slash command routing.

    Uses Protocol-based HandlerContext to decouple from App class,
    enabling easier testing and future extensibility.
    """

    def __init__(self, context: HandlerContext):
        self._context = context

        # Command map: command -> handler method
        self._command_map: Dict[str, Callable[[str], Awaitable[None]]] = {
            "/intent": self._handle_intent,
            "/analyze": self._handle_analyze,
            "/explore": self._handle_explore,
            "/connect": self._handle_connect,
            "/project": self._handle_project,
            "/login": self._handle_login,
            "/report": self._handle_report,
            "/help": self._handle_help,
            "/errors": self._handle_errors,
            "/quit": self._handle_quit,
            "/exit": self._handle_quit,  # Alias for /quit
        }

    def can_handle(self, cmd: str) -> bool:
        """Check if command is recognized."""
        return cmd.lower() in self._command_map

    async def handle(self, cmd_text: str) -> None:
        """
        Route command to appropriate handler.

        Args:
            cmd_text: Full command string (e.g., "/explore sales_data")
        """
        from textual.widgets import VerticalScroll
        from backend.orchestrator.message_components import MessageBubble

        parts = cmd_text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handler = self._command_map.get(cmd)
        if handler:
            await handler(args)
        else:
            chat_log = self._context.query_one("#chat-log", VerticalScroll)
            msg = MessageBubble(
                role="system",
                content=f"[red]알 수 없는 명령어입니다: {cmd}[/red]"
            )
            chat_log.mount(msg)
            chat_log.scroll_end(animate=False)

    async def _handle_intent(self, args: str) -> None:
        """Handle /intent command - analysis planning."""
        # Delegate to context's run_analysis with intent mode
        await self._context.run_analysis(f"[INTENT] {args}" if args else "[INTENT]")

    async def _handle_analyze(self, args: str) -> None:
        """Handle /analyze command - deep analysis."""
        if not args:
            self._show_message("[yellow]/analyze 명령어에 분석할 내용을 입력하세요.[/yellow]")
            return
        await self._context.run_analysis(args)

    async def _handle_explore(self, args: str) -> None:
        """Handle /explore command - data exploration."""
        await self._context.run_explore(args if args else None)

    async def _handle_connect(self, args: str) -> None:
        """Handle /connect command - open connection screen."""
        from backend.orchestrator.screens import ConnectionScreen
        self._context.push_screen(ConnectionScreen())

    async def _handle_project(self, args: str) -> None:
        """Handle /project command - open project screen."""
        from backend.orchestrator.screens import ProjectScreen
        self._context.push_screen(ProjectScreen())

    async def _handle_login(self, args: str) -> None:
        """Handle /login command - open auth screen."""
        from backend.orchestrator.screens import AuthScreen
        self._context.push_screen(AuthScreen())

    async def _handle_report(self, args: str) -> None:
        """Handle /report command - generate report."""
        self._show_message("[yellow]리포트 생성 기능은 준비 중입니다.[/yellow]")

    async def _handle_help(self, args: str) -> None:
        """Handle /help command - show help text."""
        help_content = (
            "[bold cyan]◈ BI-Agent 사용 가이드 ◈[/bold cyan]\n\n"
            "[bold #38bdf8]명령어 일람:[/bold #38bdf8]\n"
            "• [b]/intent[/b] : 분석 계획 수립 (예: /intent 매출 분석)\n"
            "• [b]/analyze[/b] : 데이터 심층 분석 (예: /analyze 매출 추이)\n"
            "• [b]/explore[/b] : 데이터 탐색 (예: /explore, /explore sales)\n"
            "• [b]/connect[/b] : 데이터 소스 연결\n"
            "• [b]/project[/b] : 프로젝트 전환\n"
            "• [b]/login[/b] : LLM 인증 설정\n"
            "• [b]/report[/b] : 리포트 생성\n"
            "• [b]/errors[/b] : 시스템 에러 로그 확인\n"
            "• [b]/quit, /exit[/b] : 앱 종료\n\n"
            "[bold #38bdf8]단축키:[/bold #38bdf8]\n"
            "• [b]q[/b] : 앱 종료\n"
            "• [b]/[/b] : 명령어 입력 포커스\n"
            "• [b]↑/↓[/b] : 명령어 히스토리 탐색\n"
            "• [b]tab[/b] : 명령어 자동 완성 및 입력 보조\n"
            "• [b]ctrl+l[/b] : 채팅 초기화\n"
            "• [b]F1[/b] : 도움말 표시\n"
            "• [b]ctrl+e[/b] : 에러 로그 창 열기\n\n"
            "[dim]Tip: 오른쪽 사이드바의 'ACTION RECOMMENDATION'에서 항상 다음 단계를 확인하세요![/dim]"
        )
        self._show_message(help_content)

    async def _handle_errors(self, args: str) -> None:
        """Handle /errors command - show error viewer."""
        self._context.show_error_viewer()

    async def _handle_quit(self, args: str) -> None:
        """Handle /quit and /exit commands."""
        # Import here to avoid circular dependency
        from textual.app import App
        # Access the actual app instance through context
        if hasattr(self._context, 'app'):
            await self._context.app.action_quit()
        else:
            await self._context.action_quit()

    def _show_message(self, content: str) -> None:
        """Helper to show a message in chat log."""
        from textual.widgets import VerticalScroll
        from backend.orchestrator.message_components import MessageBubble

        chat_log = self._context.query_one("#chat-log", VerticalScroll)
        msg = MessageBubble(role="system", content=content)
        chat_log.mount(msg)
        chat_log.scroll_end(animate=False)
```

**Acceptance Criteria:**
- [ ] All 11 slash commands work correctly (/intent, /analyze, /explore, /connect, /project, /login, /report, /help, /errors, /quit, /exit)
- [ ] Command arguments passed correctly
- [ ] Error handling preserved (unknown command message)
- [ ] Chat log updates preserved
- [ ] Handlers can access app UI via HandlerContext protocol

---

### Task 3.2: Extract InputHandler
**File:** `backend/orchestrator/handlers/input_handler.py`

**Source Lines:** 1319-1545 from `bi_agent_console.py`

**Steps:**
1. Create `input_handler.py`
2. Create `InputHandler` class with:
   - `__init__(self, context: HandlerContext, command_history: CommandHistory)`
   - `on_key(self, event)` - main key handler
   - `on_input_changed(self, event)` - input change handler
   - `_handle_history_navigation(self, event)` - up/down arrows
   - `_handle_tab_completion(self, event)` - tab key
   - `_handle_palette_navigation(self, event)` - arrow keys in palette
3. Extract key handling logic from `on_key` method
4. Keep reference to command_history and palette

**Acceptance Criteria:**
- [ ] Up/Down history navigation works
- [ ] Tab completion for commands works
- [ ] Tab completion for Korean phrases works
- [ ] Palette navigation with arrows works
- [ ] Enter executes selected command
- [ ] `/` key focuses input and adds slash

---

### Task 4.1: Refactor BI_AgentConsole
**File:** `backend/orchestrator/bi_agent_console.py`

**Steps:**
1. Remove extracted modal screen classes
2. Add imports for extracted modules:
   ```python
   from backend.orchestrator.screens import AuthScreen, ConnectionScreen, ProjectScreen
   from backend.orchestrator.handlers import CommandHandler, InputHandler
   from backend.orchestrator.components.sidebar_manager import SidebarManager
   ```
3. In `__init__`:
   - Initialize `self.command_handler = CommandHandler(self)`
   - Initialize `self.input_handler = InputHandler(self, self.command_history)`
   - Initialize `self.sidebar_manager = SidebarManager(self)`
4. Delegate methods:
   - `handle_command` -> `self.command_handler.handle`
   - `on_key` -> `self.input_handler.on_key`
   - `_update_sidebar` -> `self.sidebar_manager.update`
5. Implement `HandlerContext` protocol methods in App class:
   - `run_analysis` wrapper for `_run_analysis`
   - `run_explore` wrapper for `_run_explore`
   - `show_error_viewer` method
6. Keep in main app:
   - CSS styles
   - BINDINGS
   - COMMAND_LIST
   - `compose()` method
   - `on_mount()` method
   - Worker task methods (`_run_analysis`, `_run_explore`, `_run_scan`)
   - Action methods (`action_clear_chat`, `action_quit`, etc.)
   - `on_exception` handler

**Acceptance Criteria:**
- [ ] File under 500 lines
- [ ] All functionality preserved
- [ ] No import errors
- [ ] Clean separation of concerns
- [ ] App implements HandlerContext protocol

---

### Task 4.2: Update External Imports
**Files to check:**
- Any file importing from `bi_agent_console.py`

**Steps:**
1. Search for imports of `AuthScreen`, `ConnectionScreen`, `ProjectScreen` from `bi_agent_console`
2. Update to import from new locations
3. Verify no circular imports

**Acceptance Criteria:**
- [ ] No import errors on startup
- [ ] `grep` finds no old import patterns

---

### Task 5.1: Verification Testing
**Steps:**
1. Launch application with `python -m backend.orchestrator.bi_agent_console`
2. Test each slash command
3. Test keyboard shortcuts
4. Test modal screens
5. Verify sidebar updates
6. Test command history
7. Test error viewer

**Test Checklist:**
- [ ] App launches without errors
- [ ] Banner and welcome message display
- [ ] **F1 shows help (BUG FIX VERIFICATION)** - This MUST pass after Task 0.1
- [ ] `/login` opens auth screen, can select provider, can save key
- [ ] `/connect` opens connection screen, can create/edit/delete connections
- [ ] `/project` opens project screen, can switch projects
- [ ] `/explore` lists connections, tables, schemas
- [ ] `/analyze` triggers analysis workflow
- [ ] `/help` shows help text (same content as F1)
- [ ] `/report` shows "준비 중" message (or generates report if implemented)
- [ ] `/errors` opens error viewer
- [ ] `/quit` and `/exit` close app
- [ ] `q` key quits app
- [ ] `ctrl+l` clears chat
- [ ] Up/Down arrows navigate history
- [ ] Tab completes commands
- [ ] Sidebar updates automatically
- [ ] Command palette filters correctly

---

### Task 5.2: Final Import Cleanup
**Steps:**
1. Run `grep -r "from backend.orchestrator.bi_agent_console import"` to find all imports
2. Update any found imports to use new paths
3. Run application again to verify

**Acceptance Criteria:**
- [ ] Zero references to old class locations
- [ ] All tests pass (if any exist)

---

## Commit Strategy

### Commit 0: Critical Bug Fixes
```
fix(console): resolve F1 help and AuthScreen sidebar bugs

- Fix action_show_help calling non-existent _run_help method
- Fix AuthScreen._save_api_key calling self._update_sidebar instead of self.app._update_sidebar
- Both bugs caused AttributeError on user actions
```

### Commit 1: Extract Modal Screens
```
feat(screens): extract AuthScreen, ConnectionScreen, ProjectScreen

- Move AuthScreen to screens/auth_screen.py
- Move ConnectionScreen to screens/connection_screen.py
- Move ProjectScreen to screens/project_screen.py
- Update screens/__init__.py exports
```

### Commit 2: Extract Components
```
feat(components): add SidebarManager and CommandPalette

- Create components/sidebar_manager.py for sidebar update logic
- Create components/command_palette.py for command menu logic
- Add components/__init__.py
```

### Commit 3: Extract Handlers with Protocol Pattern
```
feat(handlers): add CommandHandler and InputHandler with Protocol design

- Create handlers/protocols.py with HandlerContext, CommandHandlerProtocol
- Create handlers/command_handler.py using Mediator pattern
- Create handlers/input_handler.py for keyboard/input handling
- Add handlers/__init__.py
```

### Commit 4: Refactor Main App
```
refactor(bi_agent_console): modularize using extracted components

- Reduce bi_agent_console.py from 1883 to ~400 lines
- Implement HandlerContext protocol in App class
- Delegate to CommandHandler, InputHandler, SidebarManager
- Update imports to use new screen locations
- No functionality changes
```

### Commit 5: Cleanup (if needed)
```
chore: update external imports for refactored modules
```

---

## Success Criteria

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| Main file lines | 1883 | <500 | Pending |
| Modal screens in main file | 3 | 0 | Pending |
| Distinct concerns in main file | 12+ | 5 | Pending |
| Circular dependencies | Unknown | 0 | Pending |
| Test failures | 0 | 0 | Pending |
| Functionality regressions | N/A | 0 | Pending |
| F1 Help Bug | Broken | Fixed | Pending |
| AuthScreen Sidebar Bug | Broken | Fixed | Pending |

---

## Risk Assessment

### High Risk
| Risk | Mitigation |
|------|------------|
| `self.app` references in extracted screens may break | Keep `app` property access pattern; screens already use `self.app.conn_mgr` |
| Command handler async flow may have race conditions | Maintain same `asyncio.create_task` patterns |

### Medium Risk
| Risk | Mitigation |
|------|------------|
| CSS scoping may break with extraction | Keep CSS in each class as currently done |
| Logger name collisions | Use unique logger names per module |
| Import order issues | Follow existing import patterns in codebase |
| Protocol not satisfied by App | Add explicit methods to App that match protocol |

### Low Risk
| Risk | Mitigation |
|------|------------|
| Sidebar timer may not reschedule | Keep same `self.set_timer(10, ...)` pattern |
| Command history state | Pass reference, don't recreate |

---

## Metis Critique Review (Updated)

### Critical Issues Addressed:
1. **FIXED**: Added Task 0.1 to fix missing `_run_help` method
2. **FIXED**: Updated test checklist (Task 5.1) to explicitly verify F1 bug fix
3. **FIXED**: Added explicit `screens/__init__.py` update code (Task 1.4)
4. **FIXED**: Added `/report` and `/exit` handlers to CommandHandler command map in Task 3.1
5. **INCORPORATED**: Architect's Protocol-based Mediator pattern design in Task 3.0 and 3.1

### Architectural Decisions Incorporated:
- **HandlerContext Protocol**: Defines app capabilities available to handlers
- **Mediator Pattern**: CommandHandler routes commands while keeping worker methods in App
- **Structural Typing**: Using Python's Protocol for loose coupling
- **Callback Interface**: Worker methods stay in App (they need UI access), handlers call via context

---

## Notes

- The `screens/` directory already has `__init__.py` which exports `TableSelectionScreen` and `VisualAnalysisScreen`
- ConnectionScreen is the largest and most complex extraction (~500 lines with SSH handling)
- Consider if InputHandler should be merged with CommandPalette for cohesion
- Worker methods (`_run_explore`, `_run_scan`, `_run_analysis`) could be further extracted to a `workers/` module in future iterations
- Protocol-based design enables future Handler types (KeyboardHandler, EventHandler, etc.)

---

*Plan generated by Prometheus (Planner Agent) - Iteration 2*
*Critic feedback addressed, Architect recommendations incorporated*
*Ready for implementation via `/start-work bi-agent-console-refactoring`*
