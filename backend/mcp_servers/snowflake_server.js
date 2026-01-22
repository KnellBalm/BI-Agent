#!/usr/bin/env node
const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} = require("@modelcontextprotocol/sdk/types.js");
const snowflake = require("snowflake-sdk");

/**
 * Snowflake MCP Server
 * Implementation for Snowflake data warehouse connectivity using snowflake-sdk.
 */

const server = new Server(
    {
        name: "snowflake-mcp-server",
        version: "0.1.0",
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

// Helper function to execute query
async function executeSnowflakeQuery(connectionConfig, sql) {
    const connection = snowflake.createConnection(connectionConfig);

    return new Promise((resolve, reject) => {
        connection.connect((err, conn) => {
            if (err) {
                reject(new Error(`Unable to connect: ${err.message}`));
                return;
            }

            conn.execute({
                sqlText: sql,
                complete: (err, stmt, rows) => {
                    if (err) {
                        reject(new Error(`Failed to execute query: ${err.message}`));
                    } else {
                        resolve(rows);
                    }
                    conn.destroy();
                }
            });
        });
    });
}

server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "query",
                description: "Execute a Snowflake SQL query",
                inputSchema: {
                    type: "object",
                    properties: {
                        sql: { type: "string", description: "The SQL query to execute" },
                        account: { type: "string" },
                        username: { type: "string" },
                        password: { type: "string" },
                        warehouse: { type: "string" },
                        database: { type: "string" },
                        schema: { type: "string" },
                        role: { type: "string" }
                    },
                    required: ["sql", "account", "username", "password"],
                },
            },
            {
                name: "list_tables",
                description: "List tables in a Snowflake schema",
                inputSchema: {
                    type: "object",
                    properties: {
                        account: { type: "string" },
                        username: { type: "string" },
                        password: { type: "string" },
                        database: { type: "string" },
                        schema: { type: "string" }
                    },
                    required: ["account", "username", "password", "database", "schema"]
                }
            }
        ],
    };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    const connectionConfig = {
        account: args.account,
        username: args.username,
        password: args.password,
        warehouse: args.warehouse,
        database: args.database,
        schema: args.schema,
        role: args.role
    };

    if (name === "query") {
        try {
            const rows = await executeSnowflakeQuery(connectionConfig, args.sql);
            return {
                content: [{ type: "text", text: JSON.stringify(rows, null, 2) }],
            };
        } catch (error) {
            return {
                content: [{ type: "text", text: `Error: ${error.message}` }],
                isError: true
            };
        }
    }

    if (name === "list_tables") {
        try {
            const sql = `SELECT table_name FROM ${args.database}.information_schema.tables WHERE table_schema = '${args.schema}'`;
            const rows = await executeSnowflakeQuery(connectionConfig, sql);
            return {
                content: [{ type: "text", text: JSON.stringify(rows, null, 2) }],
            };
        } catch (error) {
            return {
                content: [{ type: "text", text: `Error: ${error.message}` }],
                isError: true
            };
        }
    }

    throw new Error(`Tool not found: ${name}`);
});

async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
}

main().catch(console.error);
