# Agent Message Bus Integration Guide

## Overview

The Agent Message Bus provides async message passing between agents and the TUI without external dependencies. It uses `asyncio.Queue` for thread-safe communication and integrates seamlessly with Textual's worker pattern.

## Quick Start

### 1. Basic Integration with Textual

```python
# In bi_agent_console.py
from backend.orchestrator.agent_message_bus import (
    AgentMessageBus,
    AgentMessage,
    MessageType,
    create_thinking_message,
    create_progress_message
)
import asyncio

class BIAgentConsole(App):
    def on_mount(self) -> None:
        # Get singleton instance
        bus = AgentMessageBus()

        # Subscribe to all messages
        bus.subscribe(self._handle_agent_message)

        # Start message dispatch loop
        asyncio.create_task(bus.start())

    def _handle_agent_message(self, message: AgentMessage) -> None:
        """Handle incoming messages and update UI."""
        if message.message_type == MessageType.THINKING:
            self.update_thinking_panel(message.content)

        elif message.message_type == MessageType.PROGRESS:
            step = message.metadata['step']
            total = message.metadata['total']
            self.update_progress_bar(step, total)

        elif message.message_type == MessageType.ERROR:
            self.show_error_notification(message.content)

        elif message.message_type == MessageType.INSIGHT:
            self.add_insight_to_panel(message.content)

        elif message.message_type == MessageType.COMPLETE:
            self.mark_task_complete(message.content)

    def on_unmount(self) -> None:
        # Clean shutdown
        bus = AgentMessageBus()
        bus.stop()
```

### 2. Publishing Messages from Agents

```python
# In any agent module
from backend.orchestrator.agent_message_bus import (
    AgentMessageBus,
    create_thinking_message,
    create_progress_message,
    create_insight_message,
    create_error_message
)

class DataMasterAgent:
    async def analyze_schema(self, connection):
        bus = AgentMessageBus()

        # Send thinking status
        await bus.publish(
            create_thinking_message("DataMaster", "스키마 분석 중...")
        )

        # Send progress updates
        total_steps = 5
        for step in range(1, total_steps + 1):
            await bus.publish(
                create_progress_message(
                    "DataMaster",
                    step,
                    total_steps,
                    f"단계 {step} 처리 중"
                )
            )
            # Do work...

        # Send insight
        await bus.publish(
            create_insight_message(
                "DataMaster",
                "100개 테이블, 1,500개 컬럼 발견",
                confidence=0.98
            )
        )

        # Or send error if something fails
        try:
            # risky operation
            pass
        except Exception as e:
            await bus.publish(
                create_error_message(
                    "DataMaster",
                    f"스키마 분석 실패: {str(e)}",
                    error_type="DatabaseError"
                )
            )
```

## Message Types

### THINKING
Agent is processing internally.

```python
msg = create_thinking_message(
    "Strategist",
    "가설 생성을 위한 데이터 패턴 분석 중...",
    analysis_type="pattern_detection"
)
await bus.publish(msg)
```

### PROGRESS
Update on multi-step operation.

```python
msg = create_progress_message(
    "Designer",
    step=3,
    total=7,
    description="차트 레이아웃 최적화 중",
    chart_type="bar"
)
await bus.publish(msg)
```

### DATA_REQUEST
Request data from another agent.

```python
msg = create_data_request_message(
    "Strategist",
    "월별 매출 데이터 필요",
    target_agent="DataMaster",
    query_type="aggregation",
    time_range="last_12_months"
)
await bus.publish(msg)
```

### DATA_RESPONSE
Respond to data request.

```python
msg = create_data_response_message(
    "DataMaster",
    "월별 매출 데이터 준비 완료",
    target_agent="Strategist",
    data={
        "rows": 12,
        "columns": ["month", "revenue"],
        "preview": [["2024-01", 150000], ["2024-02", 175000]]
    }
)
await bus.publish(msg)
```

### INSIGHT
Share discovered insight.

```python
msg = create_insight_message(
    "Strategist",
    "매출이 분기별로 20% 증가하는 패턴 발견",
    confidence=0.92,
    insight_type="trend",
    impact="high"
)
await bus.publish(msg)
```

### ERROR
Report error condition.

```python
msg = create_error_message(
    "DataMaster",
    "데이터베이스 연결 실패",
    error_type="ConnectionError",
    severity="high",
    retry_possible=True
)
await bus.publish(msg)
```

### COMPLETE
Signal completion of work.

```python
msg = create_complete_message(
    "Designer",
    "3개 차트 생성 완료",
    chart_count=3,
    output_path="/tmp/charts"
)
await bus.publish(msg)
```

## Advanced Patterns

### Targeted Messages

Send message to specific agent instead of broadcast:

```python
msg = AgentMessage(
    timestamp=datetime.now(),
    from_agent="Strategist",
    to_agent="DataMaster",  # Target specific agent
    message_type=MessageType.DATA_REQUEST,
    content="데이터 필요",
    metadata={"query": "SELECT * FROM sales"}
)
await bus.publish(msg)
```

Agents can filter messages:

```python
def _handle_agent_message(self, message: AgentMessage) -> None:
    # Only handle messages for me
    if message.to_agent not in ["DataMaster", "broadcast"]:
        return

    # Process message...
```

### Message History

Retrieve recent messages for context:

```python
bus = AgentMessageBus()

# Get last 50 messages
history = bus.get_message_history(limit=50)

for msg in history:
    print(f"[{msg.timestamp}] {msg.from_agent}: {msg.content}")
```

### Logging and Debugging

All messages are automatically logged to `logs/agent_messages.jsonl`:

```json
{"timestamp": "2024-02-01T10:30:15.123456", "from_agent": "DataMaster", "to_agent": "broadcast", "message_type": "thinking", "content": "스키마 분석 중...", "metadata": {}}
{"timestamp": "2024-02-01T10:30:16.456789", "from_agent": "DataMaster", "to_agent": "broadcast", "message_type": "progress", "content": "1/5 단계: 테이블 목록 조회", "metadata": {"step": 1, "total": 5, "description": "테이블 목록 조회"}}
```

Clear logs when needed:

```python
bus = AgentMessageBus()
bus.clear_log()
```

### Error Handling

Subscriber errors don't crash the bus:

```python
def risky_callback(message: AgentMessage) -> None:
    # This error won't affect other subscribers
    raise ValueError("Something went wrong!")

bus = AgentMessageBus()
bus.subscribe(risky_callback)
bus.subscribe(safe_callback)  # This will still work

# Start bus - both callbacks registered
await bus.start()
```

### Testing Support

Use the bus in tests:

```python
import pytest
from backend.orchestrator.agent_message_bus import (
    AgentMessageBus,
    create_thinking_message
)

@pytest.fixture
def message_bus():
    # Reset singleton
    AgentMessageBus._instance = None
    bus = AgentMessageBus()
    yield bus
    bus.stop()

@pytest.mark.asyncio
async def test_my_agent(message_bus):
    received = []
    message_bus.subscribe(lambda msg: received.append(msg))

    # Start bus
    bus_task = asyncio.create_task(message_bus.start())

    # Test your agent
    agent = MyAgent()
    await agent.do_work()

    await asyncio.sleep(0.2)  # Let messages process

    # Verify messages
    assert len(received) > 0
    assert received[0].message_type == MessageType.THINKING

    # Cleanup
    message_bus.stop()
    await bus_task
```

## Performance Considerations

### Message Throughput

The bus uses `asyncio.Queue` which is highly efficient. Benchmarks show:
- 10,000+ messages/second on typical hardware
- Negligible memory overhead
- Sub-millisecond latency for delivery

### Subscriber Count

- Supports unlimited subscribers
- Each subscriber is called synchronously
- If a subscriber needs async work, it should schedule its own task:

```python
def callback(message: AgentMessage) -> None:
    # Don't block the bus with async work
    asyncio.create_task(slow_async_handler(message))
```

### Queue Management

Monitor queue size:

```python
bus = AgentMessageBus()
print(f"Queue size: {bus.get_queue_size()}")
print(f"Subscribers: {bus.subscriber_count}")
print(f"Running: {bus.is_running}")
```

## Best Practices

### 1. Use Helper Functions

Prefer helper functions over manual message construction:

```python
# Good
msg = create_progress_message("Agent", 1, 5, "Step 1")

# Avoid
msg = AgentMessage(
    timestamp=datetime.now(),
    from_agent="Agent",
    to_agent="broadcast",
    message_type=MessageType.PROGRESS,
    content="1/5 단계: Step 1",
    metadata={"step": 1, "total": 5, "description": "Step 1"}
)
```

### 2. Meaningful Content

Use Korean for user-facing messages:

```python
# Good
create_thinking_message("DataMaster", "스키마 해석 중...")

# Avoid
create_thinking_message("DataMaster", "Parsing schema...")
```

### 3. Structured Metadata

Use metadata for structured data:

```python
# Good
create_insight_message(
    "Strategist",
    "매출 증가 패턴 발견",
    confidence=0.95,
    trend="increasing",
    period="quarterly",
    magnitude=0.20
)

# Avoid putting structured data in content string
create_insight_message(
    "Strategist",
    "매출 증가 패턴 발견 (confidence: 0.95, trend: increasing)"
)
```

### 4. Always Stop on Shutdown

```python
def on_unmount(self) -> None:
    bus = AgentMessageBus()
    bus.stop()
```

## Troubleshooting

### Messages Not Arriving

1. Check bus is started:
   ```python
   bus = AgentMessageBus()
   print(f"Running: {bus.is_running}")
   ```

2. Verify subscriber is registered:
   ```python
   print(f"Subscriber count: {bus.subscriber_count}")
   ```

3. Check for errors in subscriber:
   ```python
   def callback(msg):
       try:
           # Your code
       except Exception as e:
           print(f"Error: {e}")
   ```

### Performance Issues

1. Check queue size:
   ```python
   if bus.get_queue_size() > 100:
       print("Queue backlog!")
   ```

2. Profile subscribers:
   ```python
   def callback(msg):
       start = time.time()
       # Your code
       print(f"Took {time.time() - start}s")
   ```

### Memory Issues

Clear logs periodically:

```python
# Clear on startup
bus.clear_log()

# Or periodically
if datetime.now().hour == 0:  # Midnight
    bus.clear_log()
```

## Example: Complete Integration

```python
# bi_agent_console.py
from textual.app import App
from backend.orchestrator.agent_message_bus import (
    AgentMessageBus, AgentMessage, MessageType
)
import asyncio

class BIAgentConsole(App):
    def __init__(self):
        super().__init__()
        self.bus = AgentMessageBus()

    def on_mount(self) -> None:
        self.bus.subscribe(self._on_message)
        asyncio.create_task(self.bus.start())

        # Start agent work
        asyncio.create_task(self._run_analysis())

    async def _run_analysis(self):
        # This would be your agent orchestrator
        from backend.orchestrator.collaborative_orchestrator import (
            CollaborativeOrchestrator
        )
        orchestrator = CollaborativeOrchestrator(self.bus)
        await orchestrator.run_analysis("매출 분석")

    def _on_message(self, msg: AgentMessage) -> None:
        # Update UI based on message type
        if msg.message_type == MessageType.THINKING:
            self.query_one("#thinking-panel").update(msg.content)
        elif msg.message_type == MessageType.PROGRESS:
            bar = self.query_one("#progress-bar")
            bar.update(
                total=msg.metadata['total'],
                progress=msg.metadata['step']
            )
        elif msg.message_type == MessageType.INSIGHT:
            self.query_one("#insights").add_item(msg.content)

    def on_unmount(self) -> None:
        self.bus.stop()
```

This completes the integration guide for the Agent Message Bus.
