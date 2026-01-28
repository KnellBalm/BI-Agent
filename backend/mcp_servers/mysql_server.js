#!/usr/bin/env node

/**
 * MySQL MCP Server
 *
 * MCP 서버로 MySQL 데이터베이스에 연결하고 쿼리를 실행합니다.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import mysql from 'mysql2/promise';
import dotenv from 'dotenv';

dotenv.config();

// MySQL 연결 풀 생성
const pool = mysql.createPool({
  host: process.env.MYSQL_HOST || 'localhost',
  port: parseInt(process.env.MYSQL_PORT || '3306'),
  database: process.env.MYSQL_DB,
  user: process.env.MYSQL_USER,
  password: process.env.MYSQL_PASSWORD,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
});

// MCP 서버 생성
const server = new Server(
  {
    name: 'mysql-mcp-server',
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
        description: 'Execute a read-only SQL query on MySQL database',
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
        description: 'List all tables in the current MySQL database',
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

        const [rows] = await pool.query(sql);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                rows: rows,
                rowCount: Array.isArray(rows) ? rows.length : 0,
              }, null, 2),
            },
          ],
        };
      }

      case 'list_tables': {
        const [rows] = await pool.query('SHOW TABLES');
        const tableNames = rows.map(row => Object.values(row)[0]);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(tableNames, null, 2),
            },
          ],
        };
      }

      case 'describe_table': {
        const { table_name } = args;
        const [rows] = await pool.query(`DESCRIBE ${mysql.escapeId(table_name)}`);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(rows, null, 2),
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
  console.error('MySQL MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
