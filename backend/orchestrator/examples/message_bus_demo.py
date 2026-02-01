#!/usr/bin/env python3
"""
Demo script for Agent Message Bus

This demonstrates the basic usage of the message bus with simulated agents.
Run this to see how messages flow through the system.

Usage:
    python3 backend/orchestrator/examples/message_bus_demo.py
"""

import asyncio
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from backend.orchestrator.agent_message_bus import (
    AgentMessageBus,
    AgentMessage,
    MessageType,
    create_thinking_message,
    create_progress_message,
    create_insight_message,
    create_data_request_message,
    create_data_response_message,
    create_complete_message,
    create_error_message,
)


class SimulatedAgent:
    """Simulated agent that publishes messages."""

    def __init__(self, name: str, bus: AgentMessageBus):
        self.name = name
        self.bus = bus

    async def do_work(self, task_name: str):
        """Simulate agent doing work with various message types."""
        # Thinking
        await self.bus.publish(
            create_thinking_message(
                self.name,
                f"{task_name} 분석 시작..."
            )
        )
        await asyncio.sleep(0.5)

        # Progress updates
        total_steps = 5
        for step in range(1, total_steps + 1):
            await self.bus.publish(
                create_progress_message(
                    self.name,
                    step,
                    total_steps,
                    f"{task_name} 처리 중 - 단계 {step}"
                )
            )
            await asyncio.sleep(0.3)

        # Insight
        await self.bus.publish(
            create_insight_message(
                self.name,
                f"{task_name} 완료: 중요한 패턴 발견됨",
                confidence=0.87
            )
        )
        await asyncio.sleep(0.2)

        # Complete
        await self.bus.publish(
            create_complete_message(
                self.name,
                f"{task_name} 작업 완료",
                duration_seconds=2.0
            )
        )


class SimulatedTUI:
    """Simulated TUI that receives messages."""

    def __init__(self, bus: AgentMessageBus):
        self.bus = bus
        self.message_count = 0

    def start(self):
        """Subscribe to messages."""
        self.bus.subscribe(self.handle_message)

    def handle_message(self, message: AgentMessage):
        """Handle received message and print to console."""
        self.message_count += 1

        # Format timestamp
        time_str = message.timestamp.strftime("%H:%M:%S.%f")[:-3]

        # Color based on message type
        colors = {
            MessageType.THINKING: "\033[36m",    # Cyan
            MessageType.PROGRESS: "\033[33m",    # Yellow
            MessageType.INSIGHT: "\033[32m",     # Green
            MessageType.ERROR: "\033[31m",       # Red
            MessageType.COMPLETE: "\033[35m",    # Magenta
            MessageType.DATA_REQUEST: "\033[34m",  # Blue
            MessageType.DATA_RESPONSE: "\033[34m", # Blue
        }
        reset = "\033[0m"
        color = colors.get(message.message_type, reset)

        # Format message
        print(f"{color}[{time_str}] {message.from_agent:15} | "
              f"{message.message_type.value:15} | {message.content}{reset}")

        # Show metadata if present
        if message.metadata:
            important_keys = ['step', 'total', 'confidence', 'error_type']
            relevant = {k: v for k, v in message.metadata.items()
                       if k in important_keys}
            if relevant:
                print(f"  └─ {relevant}")


async def demo_basic_flow():
    """Demonstrate basic message flow."""
    print("\n" + "="*80)
    print("DEMO 1: Basic Agent Message Flow")
    print("="*80 + "\n")

    bus = AgentMessageBus()
    tui = SimulatedTUI(bus)
    tui.start()

    # Start bus
    bus_task = asyncio.create_task(bus.start())

    # Run agents
    agent1 = SimulatedAgent("DataMaster", bus)
    agent2 = SimulatedAgent("Strategist", bus)

    await asyncio.gather(
        agent1.do_work("스키마 해석"),
        agent2.do_work("가설 생성"),
    )

    await asyncio.sleep(0.5)

    # Stop bus
    bus.stop()
    await bus_task

    print(f"\n총 {tui.message_count}개 메시지 처리됨")


async def demo_agent_communication():
    """Demonstrate agent-to-agent communication."""
    print("\n" + "="*80)
    print("DEMO 2: Agent-to-Agent Communication")
    print("="*80 + "\n")

    AgentMessageBus._instance = None  # Reset singleton
    bus = AgentMessageBus()
    tui = SimulatedTUI(bus)
    tui.start()

    bus_task = asyncio.create_task(bus.start())

    # Strategist requests data from DataMaster
    await bus.publish(
        create_data_request_message(
            "Strategist",
            "월별 매출 데이터 필요",
            target_agent="DataMaster",
            time_range="last_12_months"
        )
    )
    await asyncio.sleep(0.3)

    # DataMaster responds
    await bus.publish(
        create_data_response_message(
            "DataMaster",
            "월별 매출 데이터 준비 완료",
            target_agent="Strategist",
            data={
                "rows": 12,
                "columns": ["month", "revenue"],
                "preview": [["2024-01", 150000], ["2024-02", 175000]]
            }
        )
    )
    await asyncio.sleep(0.3)

    # Strategist analyzes
    await bus.publish(
        create_thinking_message("Strategist", "데이터 분석 중...")
    )
    await asyncio.sleep(0.5)

    # Strategist finds insight
    await bus.publish(
        create_insight_message(
            "Strategist",
            "분기별 20% 성장률 확인됨",
            confidence=0.95,
            trend="increasing"
        )
    )
    await asyncio.sleep(0.3)

    bus.stop()
    await bus_task

    print(f"\n총 {tui.message_count}개 메시지 처리됨")


async def demo_error_handling():
    """Demonstrate error handling."""
    print("\n" + "="*80)
    print("DEMO 3: Error Handling")
    print("="*80 + "\n")

    AgentMessageBus._instance = None
    bus = AgentMessageBus()
    tui = SimulatedTUI(bus)

    # Add a failing subscriber
    def failing_subscriber(msg):
        raise ValueError("Simulated subscriber error!")

    bus.subscribe(failing_subscriber)
    tui.start()  # This subscriber should still work

    bus_task = asyncio.create_task(bus.start())

    # Send messages - should not crash despite failing subscriber
    await bus.publish(
        create_thinking_message("TestAgent", "이 메시지는 전달되어야 함")
    )
    await asyncio.sleep(0.2)

    await bus.publish(
        create_error_message(
            "TestAgent",
            "시뮬레이션된 에러 발생",
            error_type="SimulatedError"
        )
    )
    await asyncio.sleep(0.2)

    bus.stop()
    await bus_task

    print(f"\n총 {tui.message_count}개 메시지 처리됨 (에러 발생에도 작동)")


async def demo_message_history():
    """Demonstrate message history retrieval."""
    print("\n" + "="*80)
    print("DEMO 4: Message History")
    print("="*80 + "\n")

    AgentMessageBus._instance = None
    bus = AgentMessageBus()
    bus.clear_log()  # Start fresh

    # Publish some messages
    for i in range(10):
        await bus.publish(
            create_thinking_message("HistoryAgent", f"메시지 {i}")
        )

    # Retrieve history
    history = bus.get_message_history(limit=5)

    print("최근 5개 메시지 (최신부터):")
    for msg in history:
        print(f"  - {msg.content}")

    print(f"\n전체 메시지 로그: {bus._log_path}")


async def main():
    """Run all demos."""
    print("\n╔════════════════════════════════════════════════════════════════╗")
    print("║          Agent Message Bus Demo                                ║")
    print("╚════════════════════════════════════════════════════════════════╝")

    await demo_basic_flow()
    await demo_agent_communication()
    await demo_error_handling()
    await demo_message_history()

    print("\n" + "="*80)
    print("All demos completed successfully!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
