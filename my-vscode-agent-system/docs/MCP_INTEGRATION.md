# MCP Integration Strategy for Ark-Lite

This document describes how Ark-Lite integrates with the Model Context Protocol (MCP) to provide extensible tool capabilities.

## Overview

MCP (Model Context Protocol) is an open protocol that enables AI assistants to securely connect to external data sources and tools. Ark-Lite integrates MCP in multiple ways:

1. **Agent-level MCP configuration** - Agents can specify MCP servers in their frontmatter
2. **Extension-level MCP client** - The VS Code extension maintains MCP connections
3. **Tool registration** - MCP tools are registered with VS Code's tool service
4. **Execution bridge** - Tool calls are routed through the MCP protocol

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Ark-Lite Extension                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     MCP Manager                              │   │
│  │                                                              │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │   │
│  │   │ GitHub MCP  │  │ Filesystem  │  │ Custom MCP  │        │   │
│  │   │ Server      │  │ MCP Server  │  │ Server      │        │   │
│  │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │   │
│  │          │                │                │                │   │
│  │          └────────────────┼────────────────┘                │   │
│  │                           │                                 │   │
│  │              ┌────────────▼────────────┐                    │   │
│  │              │      Tool Registry      │                    │   │
│  │              │                         │                    │   │
│  │              │  github_search_repos    │                    │   │
│  │              │  github_create_issue    │                    │   │
│  │              │  fs_read_file           │                    │   │
│  │              │  fs_write_file          │                    │   │
│  │              │  custom_tool_1          │                    │   │
│  │              └────────────┬────────────┘                    │   │
│  │                           │                                 │   │
│  └───────────────────────────┼─────────────────────────────────┘   │
│                              │                                      │
│              ┌───────────────▼───────────────┐                     │
│              │   VS Code Language Model      │                     │
│              │   Tools Service               │                     │
│              └───────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        MCP Servers                                   │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │ @mcp/github     │  │ @mcp/filesystem │  │ Custom Server       │ │
│  │                 │  │                 │  │                     │ │
│  │ - search_repos  │  │ - read_file     │  │ - custom_tool       │ │
│  │ - create_issue  │  │ - write_file    │  │ - another_tool      │ │
│  │ - list_prs      │  │ - list_dir      │  │                     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## MCP Server Configuration

### In Agent Files (`.github/agents/*.agent.md`)

Agents can specify MCP servers they need:

```yaml
---
name: 'GitHub Assistant'
description: 'Helps with GitHub operations'
tools: ['readFile']
mcp-servers:
  - name: 'github'
  - name: 'filesystem'
    config:
      rootPath: '${workspaceFolder}'
---

You help manage GitHub repositories using the connected MCP tools.
```

### In VS Code Settings

Global MCP server configuration:

```json
{
  "ark.mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${env:GITHUB_TOKEN}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "env": {}
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "${env:DATABASE_URL}"
      }
    }
  }
}
```

### In Workspace Configuration

Project-specific MCP configuration in `.vscode/settings.json`:

```json
{
  "ark.mcpServers": {
    "project-api": {
      "command": "node",
      "args": ["./mcp-server/index.js"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

## MCP Client Implementation

### Connection Manager

```typescript
// src/mcp/mcpConnectionManager.ts
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

export interface McpServerConfig {
  command: string;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string;
}

export class McpConnectionManager {
  private connections: Map<string, {
    client: Client;
    transport: StdioClientTransport;
    config: McpServerConfig;
  }> = new Map();

  async connect(name: string, config: McpServerConfig): Promise<Client> {
    // Resolve environment variables
    const resolvedEnv = this.resolveEnvVariables(config.env || {});
    
    const transport = new StdioClientTransport({
      command: config.command,
      args: config.args || [],
      env: { ...process.env, ...resolvedEnv },
      cwd: config.cwd
    });

    const client = new Client({
      name: `ark-lite-${name}`,
      version: '1.0.0'
    }, {
      capabilities: {
        tools: {},
        prompts: {},
        resources: {}
      }
    });

    await client.connect(transport);

    this.connections.set(name, { client, transport, config });
    
    return client;
  }

  async disconnect(name: string): Promise<void> {
    const connection = this.connections.get(name);
    if (connection) {
      await connection.client.close();
      this.connections.delete(name);
    }
  }

  async disconnectAll(): Promise<void> {
    for (const name of this.connections.keys()) {
      await this.disconnect(name);
    }
  }

  getClient(name: string): Client | undefined {
    return this.connections.get(name)?.client;
  }

  isConnected(name: string): boolean {
    return this.connections.has(name);
  }

  private resolveEnvVariables(env: Record<string, string>): Record<string, string> {
    const resolved: Record<string, string> = {};
    
    for (const [key, value] of Object.entries(env)) {
      if (value.startsWith('${env:') && value.endsWith('}')) {
        const envVar = value.slice(6, -1);
        resolved[key] = process.env[envVar] || '';
      } else {
        resolved[key] = value;
      }
    }
    
    return resolved;
  }
}
```

### Tool Discovery and Registration

```typescript
// src/mcp/mcpToolAdapter.ts
import * as vscode from 'vscode';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';

export interface McpToolDefinition {
  name: string;
  description: string;
  inputSchema: object;
  serverName: string;
}

export class McpToolAdapter {
  private toolDefinitions: Map<string, McpToolDefinition> = new Map();

  async discoverTools(serverName: string, client: Client): Promise<McpToolDefinition[]> {
    const response = await client.listTools();
    
    const tools: McpToolDefinition[] = response.tools.map(tool => ({
      name: `${serverName}_${tool.name}`,
      description: tool.description || `Tool from ${serverName}`,
      inputSchema: tool.inputSchema as object,
      serverName
    }));

    for (const tool of tools) {
      this.toolDefinitions.set(tool.name, tool);
    }

    return tools;
  }

  async registerWithVSCode(
    tools: McpToolDefinition[],
    toolsService: vscode.LanguageModelToolsService
  ): Promise<vscode.Disposable[]> {
    const disposables: vscode.Disposable[] = [];

    for (const tool of tools) {
      const disposable = toolsService.registerToolData({
        name: tool.name,
        description: tool.description,
        inputSchema: tool.inputSchema,
        tags: ['mcp', tool.serverName]
      });
      
      disposables.push(disposable);
    }

    return disposables;
  }

  getTool(name: string): McpToolDefinition | undefined {
    return this.toolDefinitions.get(name);
  }

  getAllTools(): McpToolDefinition[] {
    return Array.from(this.toolDefinitions.values());
  }
}
```

### Tool Execution

```typescript
// src/mcp/mcpToolExecutor.ts
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { McpConnectionManager } from './mcpConnectionManager.js';
import { McpToolAdapter } from './mcpToolAdapter.js';

export interface ToolCallResult {
  success: boolean;
  content: unknown;
  error?: string;
}

export class McpToolExecutor {
  constructor(
    private connectionManager: McpConnectionManager,
    private toolAdapter: McpToolAdapter
  ) {}

  async execute(
    toolName: string,
    args: Record<string, unknown>
  ): Promise<ToolCallResult> {
    // Get tool definition
    const toolDef = this.toolAdapter.getTool(toolName);
    if (!toolDef) {
      return {
        success: false,
        content: null,
        error: `Unknown tool: ${toolName}`
      };
    }

    // Get MCP client for this server
    const client = this.connectionManager.getClient(toolDef.serverName);
    if (!client) {
      return {
        success: false,
        content: null,
        error: `MCP server not connected: ${toolDef.serverName}`
      };
    }

    // Extract original tool name (without server prefix)
    const originalToolName = toolName.replace(`${toolDef.serverName}_`, '');

    try {
      // Call the tool via MCP
      const result = await client.callTool({
        name: originalToolName,
        arguments: args
      });

      return {
        success: true,
        content: result.content
      };
    } catch (error) {
      return {
        success: false,
        content: null,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  async executeWithProgress(
    toolName: string,
    args: Record<string, unknown>,
    progress: (message: string) => void
  ): Promise<ToolCallResult> {
    progress(`Executing ${toolName}...`);
    
    const result = await this.execute(toolName, args);
    
    if (result.success) {
      progress(`${toolName} completed successfully`);
    } else {
      progress(`${toolName} failed: ${result.error}`);
    }

    return result;
  }
}
```

## VS Code Integration

### Language Model Tools Service

VS Code provides `ILanguageModelToolsService` for tool registration:

```typescript
// src/mcp/vscodeToolsIntegration.ts
import * as vscode from 'vscode';
import { McpToolAdapter } from './mcpToolAdapter.js';
import { McpToolExecutor } from './mcpToolExecutor.js';

export class VSCodeToolsIntegration {
  private toolDisposables: vscode.Disposable[] = [];

  constructor(
    private toolAdapter: McpToolAdapter,
    private toolExecutor: McpToolExecutor
  ) {}

  async registerTools(): Promise<void> {
    // Get VS Code's language model tools API
    const toolsApi = vscode.lm.tools;
    
    if (!toolsApi) {
      console.warn('Language Model Tools API not available');
      return;
    }

    const tools = this.toolAdapter.getAllTools();

    for (const tool of tools) {
      const disposable = toolsApi.registerTool(tool.name, {
        description: tool.description,
        inputSchema: tool.inputSchema,
        
        prepareInvocation: async (options, token) => {
          // Prepare tool invocation
          return {
            confirmationMessages: {
              title: `Execute ${tool.name}?`,
              message: `This will execute the ${tool.name} tool.`
            }
          };
        },

        invoke: async (options, token) => {
          const result = await this.toolExecutor.execute(
            tool.name,
            options.input as Record<string, unknown>
          );

          return {
            content: [
              new vscode.LanguageModelToolResultPart(
                result.success ? result.content : result.error
              )
            ]
          };
        }
      });

      this.toolDisposables.push(disposable);
    }
  }

  dispose(): void {
    for (const disposable of this.toolDisposables) {
      disposable.dispose();
    }
    this.toolDisposables = [];
  }
}
```

## Popular MCP Servers

### GitHub MCP Server

```json
{
  "ark.mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${env:GITHUB_TOKEN}"
      }
    }
  }
}
```

Available tools:
- `github_search_repositories` - Search GitHub repositories
- `github_search_code` - Search code across repositories
- `github_create_issue` - Create GitHub issues
- `github_list_pull_requests` - List pull requests
- `github_get_file_contents` - Get file contents from a repo

### Filesystem MCP Server

```json
{
  "ark.mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "${workspaceFolder}"
      ]
    }
  }
}
```

Available tools:
- `fs_read_file` - Read file contents
- `fs_write_file` - Write file contents
- `fs_list_directory` - List directory contents
- `fs_create_directory` - Create a directory
- `fs_move_file` - Move/rename a file

### PostgreSQL MCP Server

```json
{
  "ark.mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "DATABASE_URL": "${env:DATABASE_URL}"
      }
    }
  }
}
```

Available tools:
- `postgres_query` - Execute SQL queries
- `postgres_list_tables` - List database tables
- `postgres_describe_table` - Get table schema

### Slack MCP Server

```json
{
  "ark.mcpServers": {
    "slack": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "${env:SLACK_BOT_TOKEN}",
        "SLACK_TEAM_ID": "${env:SLACK_TEAM_ID}"
      }
    }
  }
}
```

## Custom MCP Server Development

### Creating a Custom MCP Server

```typescript
// my-mcp-server/index.ts
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

const server = new Server({
  name: 'my-custom-server',
  version: '1.0.0'
}, {
  capabilities: {
    tools: {}
  }
});

// Register a custom tool
server.setRequestHandler('tools/list', async () => ({
  tools: [
    {
      name: 'my_custom_tool',
      description: 'Does something useful',
      inputSchema: {
        type: 'object',
        properties: {
          input: { type: 'string', description: 'The input' }
        },
        required: ['input']
      }
    }
  ]
}));

// Handle tool calls
server.setRequestHandler('tools/call', async (request) => {
  const { name, arguments: args } = request.params;
  
  if (name === 'my_custom_tool') {
    const result = await doSomethingUseful(args.input);
    return {
      content: [{ type: 'text', text: result }]
    };
  }
  
  throw new Error(`Unknown tool: ${name}`);
});

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
```

### Registering Custom Server

```json
{
  "ark.mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["./my-mcp-server/dist/index.js"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

## Security Considerations

### Token Management

1. **Never store tokens in code** - Use environment variables
2. **Use VS Code's secret storage** for sensitive data
3. **Limit token scopes** to minimum required permissions

```typescript
// Secure token storage
import * as vscode from 'vscode';

async function storeToken(context: vscode.ExtensionContext, key: string, token: string) {
  await context.secrets.store(key, token);
}

async function getToken(context: vscode.ExtensionContext, key: string): Promise<string | undefined> {
  return context.secrets.get(key);
}
```

### Permission Model

1. **Tool approval** - Require user confirmation for sensitive operations
2. **Server whitelisting** - Only allow known MCP servers
3. **Sandboxing** - Limit server access to workspace folder

### Audit Logging

```typescript
// Log all MCP tool calls
class McpAuditLogger {
  log(serverName: string, toolName: string, args: unknown, result: unknown) {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      server: serverName,
      tool: toolName,
      args: this.sanitize(args),
      result: result
    }));
  }

  private sanitize(args: unknown): unknown {
    // Remove sensitive fields
    if (typeof args === 'object' && args !== null) {
      const sanitized = { ...args as Record<string, unknown> };
      delete sanitized['password'];
      delete sanitized['token'];
      delete sanitized['secret'];
      return sanitized;
    }
    return args;
  }
}
```

## Troubleshooting

### Common Issues

**MCP server not connecting**
```bash
# Check if server is executable
npx -y @modelcontextprotocol/server-github --version

# Check environment variables
echo $GITHUB_TOKEN
```

**Tool not appearing**
1. Verify server is connected: Check extension output
2. Verify tool is listed: Use `ark.showMcpTools` command
3. Check tool registration: Look for errors in developer console

**Tool execution failing**
1. Check input schema matches arguments
2. Verify permissions (tokens, file access)
3. Check server logs for errors

### Debug Mode

Enable MCP debug logging:

```json
{
  "ark.debug.mcp": true
}
```

This logs all MCP protocol messages to the output channel.

## Best Practices

1. **Lazy loading** - Only connect to MCP servers when needed
2. **Connection pooling** - Reuse connections across tool calls
3. **Timeout handling** - Set reasonable timeouts for tool calls
4. **Error recovery** - Implement automatic reconnection
5. **Graceful shutdown** - Properly disconnect all servers on extension deactivation
6. **Resource cleanup** - Dispose of connections and listeners
7. **Progress reporting** - Show progress for long-running operations
8. **Caching** - Cache tool definitions to reduce discovery overhead
