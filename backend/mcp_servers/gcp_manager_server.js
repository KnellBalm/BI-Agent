#!/usr/bin/env node

/**
 * GCP Manager MCP Server
 * 
 * Google Cloud APIs (Monitoring, Billing)를 통해 할당량 및 결제 상태를 모니터링합니다.
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { MetricServiceClient } from '@google-cloud/monitoring';
import { CloudBillingClient } from '@google-cloud/billing';
import dotenv from 'dotenv';

dotenv.config();

const monitoringClient = new MetricServiceClient();
const billingClient = new CloudBillingClient();

const server = new Server(
    {
        name: 'gcp-manager-mcp-server',
        version: '1.0.0',
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

// 도구 목록 정의
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: 'get_quota_usage',
                description: 'Get current quota usage for a specific GCP service (e.g., Generative Language API)',
                inputSchema: {
                    type: 'object',
                    properties: {
                        projectId: {
                            type: 'string',
                            description: 'GCP Project ID',
                        },
                        service: {
                            type: 'string',
                            description: 'Service name (default: generativelanguage.googleapis.com)',
                            default: 'generativelanguage.googleapis.com',
                        },
                    },
                    required: ['projectId'],
                },
            },
            {
                name: 'get_billing_info',
                description: 'Get billing account information and status for a project',
                inputSchema: {
                    type: 'object',
                    properties: {
                        projectId: {
                            type: 'string',
                            description: 'GCP Project ID',
                        },
                    },
                    required: ['projectId'],
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
            case 'get_quota_usage': {
                const { projectId, service = 'generativelanguage.googleapis.com' } = args;
                const name = monitoringClient.projectPath(projectId);

                // 최근 1시간 동안의 쿼터 사용량 조회 필터
                // 참고: 실제 Gemini API의 정확한 메트릭 이름은 서비스에 따라 다를 수 있음
                const filter = `metric.type = "serviceruntime.googleapis.com/quota/rate/net_usage" AND resource.labels.service = "${service}"`;

                const [timeSeries] = await monitoringClient.listTimeSeries({
                    name,
                    filter,
                    interval: {
                        startTime: {
                            seconds: Math.floor(Date.now() / 1000) - 3600,
                        },
                        endTime: {
                            seconds: Math.floor(Date.now() / 1000),
                        },
                    },
                });

                return {
                    content: [
                        {
                            type: 'text',
                            text: JSON.stringify({
                                service,
                                usageData: timeSeries,
                                message: timeSeries.length > 0 ? "Usage data retrieved successfully." : "No usage data found for the given interval. This might mean no requests were made recently."
                            }, null, 2),
                        },
                    ],
                };
            }

            case 'get_billing_info': {
                const { projectId } = args;
                const [billingInfo] = await billingClient.getProjectBillingInfo({
                    name: `projects/${projectId}`,
                });

                return {
                    content: [
                        {
                            type: 'text',
                            text: JSON.stringify(billingInfo, null, 2),
                        },
                    ],
                };
            }

            default:
                throw new Error(`Unknown tool: ${name}`);
        }
    } catch (error) {
        console.error(`Error executing tool ${name}:`, error);
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

async function main() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('GCP Manager MCP Server running on stdio');
}

main().catch((error) => {
    console.error('Server error:', error);
    process.exit(1);
});
