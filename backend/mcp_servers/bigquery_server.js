#!/usr/bin/env node
const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} = require("@modelcontextprotocol/sdk/types.js");
const { BigQuery } = require("@google-cloud/bigquery");

/**
 * BigQuery MCP Server
 * Implementation for Google BigQuery data warehouse connectivity using @google-cloud/bigquery.
 */

const server = new Server(
    {
        name: "bigquery-mcp-server",
        version: "0.1.0",
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "query",
                description: "Execute a BigQuery SQL query",
                inputSchema: {
                    type: "object",
                    properties: {
                        sql: { type: "string", description: "The SQL query to execute" },
                        projectId: { type: "string", description: "Google Cloud Project ID" },
                        location: { type: "string", description: "Dataset location" },
                    },
                    required: ["sql"],
                },
            },
            {
                name: "list_datasets",
                description: "List datasets in a project",
                inputSchema: {
                    type: "object",
                    properties: {
                        projectId: { type: "string" }
                    }
                }
            },
            {
                name: "list_tables",
                description: "List tables in a dataset",
                inputSchema: {
                    type: "object",
                    properties: {
                        projectId: { type: "string" },
                        datasetId: { type: "string" }
                    },
                    required: ["datasetId"]
                }
            }
        ],
    };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    const bigquery = new BigQuery({
        projectId: args.projectId,
        location: args.location
    });

    if (name === "query") {
        try {
            const [rows] = await bigquery.query({
                query: args.sql,
                location: args.location
            });
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

    if (name === "list_datasets") {
        try {
            const [datasets] = await bigquery.getDatasets();
            const datasetIds = datasets.map(d => d.id);
            return {
                content: [{ type: "text", text: JSON.stringify(datasetIds, null, 2) }],
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
            const [tables] = await bigquery.dataset(args.datasetId).getTables();
            const tableIds = tables.map(t => t.id);
            return {
                content: [{ type: "text", text: JSON.stringify(tableIds, null, 2) }],
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
