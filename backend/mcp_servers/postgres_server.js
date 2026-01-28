#!/usr/bin/env node

/**
 * PostgreSQL MCP Server
 *
 * MCP 서버로 PostgreSQL 데이터베이스에 연결하고 쿼리를 실행합니다.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import pg from 'pg';
import dotenv from 'dotenv';

dotenv.config();

const { Pool } = pg;

// PostgreSQL 연결 풀 생성
const pool = new Pool({
  host: process.env.POSTGRES_HOST || 'localhost',
  port: parseInt(process.env.POSTGRES_PORT || '5432'),
  database: process.env.POSTGRES_DB,
  user: process.env.POSTGRES_USER,
  password: process.env.POSTGRES_PASSWORD,
  max: 10,
  idleTimeoutMillis: 30000,
});

// MCP 서버 생성
const server = new Server(
  {
    name: 'postgres-mcp-server',
    version: '0.1.0',
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
        name: 'query',
        description: 'Execute a read-only SQL query on PostgreSQL database',
        inputSchema: {
          type: 'object',
          properties: {
            sql: {
              type: 'string',
              description: 'SQL query to execute (SELECT only)',
            },
          },
          required: ['sql'],
        },
      },
      {
        name: 'list_tables',
        description: 'List all tables in the current PostgreSQL database',
        inputSchema: {
          type: 'object',
          properties: {},
        },
      },
      {
        name: 'describe_table',
        description: 'Get schema information for a specific table',
        inputSchema: {
          type: 'object',
          properties: {
            table_name: {
              type: 'string',
              description: 'Name of the table to describe',
            },
          },
          required: ['table_name'],
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
      case 'query': {
        const { sql } = args;

        // 보안: SELECT 쿼리만 허용
        if (!sql.trim().toLowerCase().startsWith('select')) {
          throw new Error('Only SELECT queries are allowed');
        }

        const result = await pool.query(sql);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                rows: result.rows,
                rowCount: result.rowCount,
              }, null, 2),
            },
          ],
        };
      }

      case 'list_tables': {
        const result = await pool.query(`
          SELECT table_name
          FROM information_schema.tables
          WHERE table_schema = 'public'
          ORDER BY table_name
        `);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result.rows.map(r => r.table_name), null, 2),
            },
          ],
        };
      }

      case 'describe_table': {
        const { table_name } = args;
        const result = await pool.query(`
          SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
          FROM information_schema.columns
          WHERE table_schema = 'public'
            AND table_name = $1
          ORDER BY ordinal_position
        `, [table_name]);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result.rows, null, 2),
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
  console.error('PostgreSQL MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
