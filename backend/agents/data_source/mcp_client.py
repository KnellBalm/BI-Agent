import asyncio
import os
from typing import Any, Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

load_dotenv()

class MCPClient:
    """
    MCP 서버와의 통신을 관리하는 클라이언트 래퍼 클래스
    """
    def __init__(self, server_path: str, args: List[str] = None, env: Dict[str, str] = None):
        self.server_parameters = StdioServerParameters(
            command="node",
            args=[server_path] + (args or []),
            env={**os.environ, **(env or {})}
        )
        self.session: Optional[ClientSession] = None
        self._exit_stack = None

    async def connect(self):
        """서버에 연결하고 세션을 시작합니다."""
        if self.session:
            return

        from contextlib import AsyncExitStack
        self._exit_stack = AsyncExitStack()
        
        # stdio_client를 사용하여 서버와 통신 채널을 엽니다.
        read_stream, write_stream = await self._exit_stack.enter_async_context(stdio_client(self.server_parameters))
        
        self.session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
        await self.session.initialize()

    async def list_tools(self) -> List[Any]:
        """사용 가능한 도구 목록을 가져옵니다."""
        if not self.session:
            await self.connect()
        
        result = await self.session.list_tools()
        return result.tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """도구를 호출합니다."""
        if not self.session:
            await self.connect()
        
        return await self.session.call_tool(name, arguments)

    async def disconnect(self):
        """연결을 종료합니다."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self.session = None
            self._exit_stack = None

async def main():
    # 테스트 코드 (PostgreSQL MCP 서버 예시)
    client = MCPClient(os.path.abspath("backend/mcp_servers/postgres_server.js"))
    try:
        await client.connect()
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
