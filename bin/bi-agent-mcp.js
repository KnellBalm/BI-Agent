#!/usr/bin/env node

/**
 * BI-Agent MCP Server
 * 
 * BI-Agent의 기능을 MCP 프로토콜로 제공하는 서버입니다.
 * Claude Desktop, Cursor 등 MCP 지원 클라이언트에서 사용 가능합니다.
 * 
 * 사용법:
 *   npx @bi-agent/mcp
 *   또는
 *   node bin/bi-agent-mcp.js
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');

// MCP 서버 생성
const server = new Server(
  {
    name: 'bi-agent',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Python Orchestrator 호출 함수
async function callOrchestrator(action, params = {}) {
  return new Promise((resolve, reject) => {
    const pythonScript = path.join(PROJECT_ROOT, 'backend', 'mcp_bridge.py');
    const input = JSON.stringify({ action, params });
    
    // venv/bin/python 우선 사용
    const venvPython = path.join(PROJECT_ROOT, 'venv', 'bin', 'python');
    const pythonCmd = venvPython; // 여기서는 항상 venv 사용하도록 강제 (로컬 테스트용)
    
    const python = spawn(pythonCmd, [pythonScript], {
      cwd: PROJECT_ROOT,
      env: { ...process.env, PYTHONPATH: PROJECT_ROOT }
    });
    
    let stdout = '';
    let stderr = '';
    
    python.stdin.write(input);
    python.stdin.end();
    
    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    
    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    
    python.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Python error (${code}): ${stderr}`));
      } else {
        try {
          resolve(JSON.parse(stdout));
        } catch (e) {
          resolve({ result: stdout.trim() });
        }
      }
    });
  });
}

// 도구 목록 제공
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'query_data',
        description: '자연어로 데이터베이스를 조회합니다. PostgreSQL, MySQL, Excel 등 다양한 데이터 소스를 지원합니다.',
        inputSchema: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: '자연어 질문 (예: "이번 달 매출 상위 10개 제품 보여줘")',
            },
            connection_id: {
              type: 'string',
              description: '사용할 데이터 연결 ID (생략 시 기본 연결 사용)',
            },
          },
          required: ['query'],
        },
      },
      {
        name: 'modify_bi',
        description: 'BI 대시보드를 수정합니다. 필드 추가, 쿼리 변경, 시각화 업데이트 등을 수행합니다.',
        inputSchema: {
          type: 'object',
          properties: {
            action: {
              type: 'string',
              description: '수행할 작업 (예: "매출 대시보드에 이익률 필드 추가해줘")',
            },
          },
          required: ['action'],
        },
      },
      {
        name: 'list_connections',
        description: '등록된 데이터베이스 연결 목록을 조회합니다.',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
      {
        name: 'register_connection',
        description: '새로운 데이터베이스 연결을 등록합니다.',
        inputSchema: {
          type: 'object',
          properties: {
            id: {
              type: 'string',
              description: '연결 ID (고유 식별자)',
            },
            type: {
              type: 'string',
              enum: ['postgres', 'mysql', 'excel'],
              description: '데이터 소스 타입',
            },
            config: {
              type: 'object',
              description: '연결 설정 (host, port, database, user, password 등)',
            },
          },
          required: ['id', 'type', 'config'],
        },
      },
    ],
  };
});

// 도구 실행 핸들러
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    let result;

    switch (name) {
      case 'query_data':
        result = await callOrchestrator('query_data', {
          query: args.query,
          connection_id: args.connection_id,
        });
        break;

      case 'modify_bi':
        result = await callOrchestrator('modify_bi', {
          action: args.action,
        });
        break;

      case 'list_connections':
        result = await callOrchestrator('list_connections', {});
        break;

      case 'register_connection':
        result = await callOrchestrator('register_connection', {
          id: args.id,
          type: args.type,
          config: args.config,
        });
        break;

      default:
        throw new Error(`Unknown tool: ${name}`);
    }

    return {
      content: [
        {
          type: 'text',
          text: typeof result === 'string' ? result : JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// 서버 시작
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('BI-Agent MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
