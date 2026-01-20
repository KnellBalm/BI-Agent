#!/usr/bin/env node

/**
 * Excel MCP Server
 *
 * MCP 서버로 Excel 파일을 읽고 쓰기를 수행합니다.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import XLSX from 'xlsx';
import fs from 'fs';
import path from 'path';

// MCP 서버 생성
const server = new Server(
  {
    name: 'excel-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// 도구 목록 제공
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'read_excel',
        description: 'Read data from an Excel file',
        inputSchema: {
          type: 'object',
          properties: {
            file_path: {
              type: 'string',
              description: 'Path to the Excel file',
            },
            sheet_name: {
              type: 'string',
              description: 'Name of the sheet to read (optional, defaults to first sheet)',
            },
            range: {
              type: 'string',
              description: 'Cell range to read (e.g., "A1:D10", optional)',
            },
          },
          required: ['file_path'],
        },
      },
      {
        name: 'list_sheets',
        description: 'List all sheet names in an Excel file',
        inputSchema: {
          type: 'object',
          properties: {
            file_path: {
              type: 'string',
              description: 'Path to the Excel file',
            },
          },
          required: ['file_path'],
        },
      },
      {
        name: 'write_excel',
        description: 'Write data to an Excel file',
        inputSchema: {
          type: 'object',
          properties: {
            file_path: {
              type: 'string',
              description: 'Path to save the Excel file',
            },
            data: {
              type: 'array',
              description: 'Array of objects to write as rows',
            },
            sheet_name: {
              type: 'string',
              description: 'Name of the sheet (optional, defaults to "Sheet1")',
            },
          },
          required: ['file_path', 'data'],
        },
      },
    ],
  };
});

// 도구 실행 핸들러
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case 'read_excel': {
        const { file_path, sheet_name, range } = args;

        // 파일 존재 확인
        if (!fs.existsSync(file_path)) {
          throw new Error(`File not found: ${file_path}`);
        }

        // Excel 파일 읽기
        const workbook = XLSX.readFile(file_path);

        // 시트 선택
        const sheetToRead = sheet_name || workbook.SheetNames[0];
        if (!workbook.Sheets[sheetToRead]) {
          throw new Error(`Sheet not found: ${sheetToRead}`);
        }

        const worksheet = workbook.Sheets[sheetToRead];

        // 데이터 변환
        let data;
        if (range) {
          data = XLSX.utils.sheet_to_json(worksheet, { range: range });
        } else {
          data = XLSX.utils.sheet_to_json(worksheet);
        }

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                sheet: sheetToRead,
                rows: data,
                rowCount: data.length,
              }, null, 2),
            },
          ],
        };
      }

      case 'list_sheets': {
        const { file_path } = args;

        if (!fs.existsSync(file_path)) {
          throw new Error(`File not found: ${file_path}`);
        }

        const workbook = XLSX.readFile(file_path);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(workbook.SheetNames, null, 2),
            },
          ],
        };
      }

      case 'write_excel': {
        const { file_path, data, sheet_name = 'Sheet1' } = args;

        // 데이터 검증
        if (!Array.isArray(data) || data.length === 0) {
          throw new Error('Data must be a non-empty array');
        }

        // 워크북 생성
        const worksheet = XLSX.utils.json_to_sheet(data);
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, sheet_name);

        // 디렉토리 생성 (없으면)
        const dir = path.dirname(file_path);
        if (!fs.existsSync(dir)) {
          fs.mkdirSync(dir, { recursive: true });
        }

        // 파일 저장
        XLSX.writeFile(workbook, file_path);

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                message: 'Excel file written successfully',
                file_path: file_path,
                rowCount: data.length,
              }, null, 2),
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
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
  console.error('Excel MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
