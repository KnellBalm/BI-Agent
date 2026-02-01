# Command History and Tab Completion

## Overview

The Command History feature provides a terminal-like experience for the BI-Agent console with:
- **Up/Down arrow navigation** through previous commands
- **Tab completion** for slash commands and Korean BI analysis phrases
- **Persistent storage** across sessions
- **Smart duplicate handling** to keep history clean

## Implementation

### Files

- **`backend/orchestrator/command_history.py`** - Core CommandHistory class
- **`backend/orchestrator/bi_agent_console.py`** - Console integration
- **`backend/tests/test_command_history.py`** - Comprehensive test suite
- **`~/.bi-agent/history.json`** - Persistent storage location

### Architecture

```
CommandHistory
├── Persistence Layer (JSON file)
├── Navigation Engine (Up/Down arrows)
├── Completion Engine (Tab key)
└── Entry Management (Add/Clear/Get)
```

## Features

### 1. History Navigation

**Up Arrow** - Navigate backward through history:
```
User types: [empty]
Press UP:   "지역별 매출 분석"  (most recent)
Press UP:   "월별 매출 추이"
Press UP:   "매출 분석"
```

**Down Arrow** - Navigate forward through history:
```
Current:    "매출 분석"
Press DOWN: "월별 매출 추이"
Press DOWN: "지역별 매출 분석"
Press DOWN: [empty]  (back to empty input)
```

### 2. Tab Completion

#### Slash Commands
```
User types: /con<TAB>
Result:     /connect
```

#### Korean BI Phrases
The system includes common Korean business intelligence phrases:
```
User types: 매출<TAB>
Suggestions: 매출, 매출 분석, 매출 추이, 매출 증감률...

User types: 지역<TAB>
Suggestions: 지역, 지역별 매출, 지역별 분석...
```

**Common phrases include:**
- 매출, 분석, 추이, 성능, 고객, 제품
- 월별, 지역, 연도별, 분기별, 일별
- 카테고리별, 상위, 하위, 비교
- 증감, 성장률, 점유율

#### History-based Completion
```
History:    ["매출 증감률 분석", "지역별 성과 리포트"]
User types: 매출<TAB>
Suggestions: 매출 증감률 분석, 매출, 매출 분석...
             ^^^^^^^^^^^^^^^^^ (from history comes first)
```

### 3. Persistent Storage

Commands are automatically saved to `~/.bi-agent/history.json`:

```json
[
  {
    "command": "매출 분석",
    "timestamp": "2024-01-01T12:00:00",
    "context": "query"
  },
  {
    "command": "/connect",
    "timestamp": "2024-01-01T13:00:00",
    "context": "slash_command"
  }
]
```

**Context types:**
- `query` - Natural language queries
- `slash_command` - Slash commands like /intent, /connect
- `intent` - Specific intent analysis requests

### 4. Duplicate Handling

Consecutive duplicate commands are automatically skipped:

```python
history.add_command("매출 분석")
history.add_command("매출 분석")  # Skipped - duplicate

# Result: Only one entry stored
```

### 5. Max Size Enforcement

History maintains only the most recent 100 commands (configurable):

```python
history = CommandHistory(max_size=100)
# Automatically keeps only the 100 most recent commands
```

## Usage in Console

### Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `↑` | Previous command | Navigate backward in history |
| `↓` | Next command | Navigate forward in history |
| `Tab` | Autocomplete | Complete slash commands or Korean phrases |
| `/` | Command menu | Show slash command palette |

### Integration Example

```python
from backend.orchestrator.command_history import CommandHistory

class BI_AgentConsole(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize command history
        self.command_history = CommandHistory()

    def on_input_submitted(self, event):
        user_text = event.value.strip()

        # Save to history
        context = "slash_command" if user_text.startswith("/") else "query"
        self.command_history.add_command(user_text, context=context)

        # Process command...

    def on_key(self, event):
        user_input = self.query_one("#user-input", Input)

        # Up arrow - previous command
        if event.key == "up":
            prev = self.command_history.get_previous()
            if prev:
                user_input.value = prev

        # Down arrow - next command
        elif event.key == "down":
            next = self.command_history.get_next()
            if next is not None:
                user_input.value = next

        # Tab - autocomplete
        elif event.key == "tab":
            current = user_input.value
            suggestions = self.command_history.get_suggestions(current)
            # Apply first suggestion...
```

## API Reference

### CommandHistory Class

#### Constructor

```python
CommandHistory(
    history_file: Optional[Path] = None,  # Defaults to ~/.bi-agent/history.json
    max_size: int = 100                   # Maximum number of commands to keep
)
```

#### Methods

**`add_command(command: str, context: str = "") -> None`**
- Add a command to history
- Automatically persists to disk
- Skips consecutive duplicates

**`get_previous() -> Optional[str]`**
- Navigate backward in history (up arrow)
- Returns previous command or None if at beginning

**`get_next() -> Optional[str]`**
- Navigate forward in history (down arrow)
- Returns next command or "" if at end

**`get_suggestions(prefix: str) -> List[str]`**
- Get completion suggestions for given prefix
- Combines history + common Korean phrases
- Returns up to 10 suggestions

**`get_all() -> List[CommandHistoryEntry]`**
- Get all history entries
- Returns a copy of the entries list

**`clear() -> None`**
- Clear all history
- Removes all entries and persists empty state

**`reset_navigation() -> None`**
- Reset navigation index
- Call when user starts typing new command

### CommandHistoryEntry Class

```python
@dataclass
class CommandHistoryEntry:
    command: str       # The command text
    timestamp: str     # ISO format datetime
    context: str = ""  # Optional context/category
```

## Testing

### Run Unit Tests

```bash
python3 -m pytest backend/tests/test_command_history.py -v
```

**Coverage:**
- Entry creation and serialization
- History persistence and loading
- Navigation (up/down arrows)
- Tab completion
- Duplicate handling
- Max size enforcement
- Legacy format migration
- Error handling (corrupted files)

### Run Manual Demonstration

```bash
python3 backend/tests/manual_test_command_history.py
```

This demonstrates all features with Korean text examples.

## Common Patterns

### Pattern 1: Basic History Navigation

```python
# User presses UP multiple times
history.get_previous()  # "최근 명령 3"
history.get_previous()  # "최근 명령 2"
history.get_previous()  # "최근 명령 1"

# User presses DOWN to go back
history.get_next()      # "최근 명령 2"
history.get_next()      # "최근 명령 3"
history.get_next()      # "" (back to empty)
```

### Pattern 2: Tab Completion with Multiple Matches

```python
prefix = "매출"
suggestions = history.get_suggestions(prefix)

if len(suggestions) == 1:
    # Auto-complete
    user_input.value = suggestions[0]
elif len(suggestions) > 1:
    # Find common prefix or show suggestions
    notify(f"Suggestions: {', '.join(suggestions[:5])}")
```

### Pattern 3: Context-aware Storage

```python
# Store different types of commands
if user_text.startswith("/"):
    history.add_command(user_text, context="slash_command")
elif is_intent_query(user_text):
    history.add_command(user_text, context="intent")
else:
    history.add_command(user_text, context="query")
```

## File Format

### Current Format (v1.0)

```json
[
  {
    "command": "매출 추이 분석",
    "timestamp": "2024-01-01T12:00:00",
    "context": "query"
  }
]
```

### Legacy Format (v0.x) - Supported

```json
[
  "매출 분석",
  "고객 세그먼트",
  "/connect"
]
```

Legacy format is automatically upgraded on load.

## Error Handling

### Corrupted History File

If the history file is corrupted:
1. Log error to diagnostic logger
2. Start with empty history
3. Continue normal operation
4. Next save will create valid file

### Missing Directory

If `~/.bi-agent/` doesn't exist:
1. Automatically create directory
2. Create new history.json
3. Continue normal operation

### Disk Full

If unable to save:
1. Log error
2. Continue with in-memory history
3. Retry on next command

## Performance

- **Load time:** < 10ms for 100 entries
- **Save time:** < 5ms per command
- **Memory:** ~1KB per 100 commands
- **Search:** O(n) for suggestions (acceptable for n ≤ 100)

## Future Enhancements

Potential improvements for future versions:

1. **Smart Ranking** - Rank suggestions by frequency and recency
2. **Fuzzy Matching** - Match partial Korean syllables
3. **Context Awareness** - Different history per data source
4. **Export/Import** - Share history between machines
5. **Search History** - Ctrl+R style reverse search
6. **Command Templates** - Save common query patterns
7. **Alias System** - Short aliases for long commands

## Migration Guide

### From No History to CommandHistory

```python
# Before (no history)
class Console(App):
    async def on_input_submitted(self, event):
        await self.process_query(event.value)

# After (with history)
class Console(App):
    def __init__(self):
        super().__init__()
        self.command_history = CommandHistory()

    async def on_input_submitted(self, event):
        # Save to history first
        self.command_history.add_command(event.value)
        await self.process_query(event.value)
```

## Troubleshooting

### History not saving

Check file permissions:
```bash
ls -la ~/.bi-agent/history.json
```

### History not loading

Check file format:
```bash
cat ~/.bi-agent/history.json | python3 -m json.tool
```

### Tab completion not working

Verify Korean locale is installed:
```bash
locale -a | grep ko_KR
```

## License

Part of BI-Agent project - internal documentation.

## Contact

For issues or questions about command history:
- File issue in BI-Agent repository
- Tag with `feature:command-history` label
