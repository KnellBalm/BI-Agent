
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";

// .env 파일 로드
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
// backend/tests/ -> backend/ -> BI-Agent/
const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const SERVER_PATH = path.join(PROJECT_ROOT, "bin", "bi-agent-mcp.js");

async function verifyMCP() {
  console.log("=== BI-Agent MCP Server 검증 시작 ===");
  
  const transport = new StdioClientTransport({
    command: "node",
    args: [SERVER_PATH],
    env: {
      ...process.env,
      GEMINI_API_KEY: process.env.GEMINI_API_KEY,
      PYTHONPATH: PROJECT_ROOT
    }
  });

  const client = new Client({
    name: "bi-agent-tester",
    version: "1.0.0"
  }, {
    capabilities: {}
  });

  try {
    console.log("1. MCP 서버 연결 중...");
    await client.connect(transport);
    console.log("   [OK] 연결 성공!");

    console.log("\n2. 사용 가능한 도구 목록:");
    const tools = await client.listTools();
    tools.tools.forEach(tool => {
      console.log(`   - ${tool.name}: ${tool.description}`);
    });

    console.log("\n3. 'list_connections' 도구 호출 테스트...");
    const connections = await client.callTool({
      name: "list_connections",
      arguments: {}
    });
    console.log("   결과:", JSON.stringify(connections.content[0].text, null, 2));

    console.log("\n✅ BI-Agent MCP 서버 검증 완료!");
  } catch (error) {
    console.error("\n❌ 검증 실패:", error);
  } finally {
    // Stdio 전송 방식에서는 세션 종료가 필요할 수 있음
    process.exit(0);
  }
}

verifyMCP();
