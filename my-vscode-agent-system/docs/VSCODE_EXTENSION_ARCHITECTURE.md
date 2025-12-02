# VS Code Extension Architecture for Ark-Lite

This document describes the architecture for integrating Ark-Lite as a VS Code extension that serves as the orchestrator for multi-agent workflows.

## Overview

The Ark-Lite VS Code extension acts as the central orchestrator, connecting:
- Custom agents defined in `.github/agents/`
- VS Code's native Copilot Chat
- MCP (Model Context Protocol) servers
- VS Code's Language Model API

```
┌─────────────────────────────────────────────────────────────────────┐
│                        VS Code Copilot Chat                         │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Mode Picker                               │   │
│  │  [Ask] [Agent ▼] [Edit]  [Orchestrator] [PM] [Reviewer]...  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Ark-Lite Extension                              │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │ Agent Loader    │  │ MCP Client      │  │ Tool Registry       │ │
│  │ (.github/agents)│  │ (Servers)       │  │ (VS Code + MCP)     │ │
│  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘ │
│           │                    │                       │            │
│           └────────────────────┼───────────────────────┘            │
│                                │                                    │
│                    ┌───────────▼───────────┐                       │
│                    │   Orchestrator Core   │                       │
│                    │  - Session Management │                       │
│                    │  - Agent Coordination │                       │
│                    │  - Conversation State │                       │
│                    └───────────┬───────────┘                       │
│                                │                                    │
│                    ┌───────────▼───────────┐                       │
│                    │   Chat Participant    │                       │
│                    │  Implementation       │                       │
│                    └───────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     VS Code APIs                                    │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │ vscode.lm       │  │ vscode.chat     │  │ vscode.workspace    │ │
│  │ (Language Model)│  │ (Participants)  │  │ (File System)       │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Extension Structure

```
vscode-ark-extension/
├── package.json              # Extension manifest
├── src/
│   ├── extension.ts          # Main entry point
│   ├── participant/
│   │   ├── arkParticipant.ts # Chat participant implementation
│   │   └── handlers.ts       # Request handlers
│   ├── agents/
│   │   ├── agentLoader.ts    # Load .github/agents/*.md
│   │   ├── agentRegistry.ts  # Agent management
│   │   └── agentRunner.ts    # Execute agent logic
│   ├── mcp/
│   │   ├── mcpClient.ts      # MCP protocol client
│   │   ├── mcpToolAdapter.ts # Adapt MCP tools to VS Code
│   │   └── mcpServers.ts     # Server management
│   ├── tools/
│   │   ├── toolRegistry.ts   # Tool registration
│   │   ├── vscodeTools.ts    # Built-in VS Code tools
│   │   └── customTools.ts    # Custom tool implementations
│   ├── orchestration/
│   │   ├── orchestrator.ts   # Multi-agent coordination
│   │   ├── session.ts        # Session management
│   │   └── workflow.ts       # Workflow execution
│   └── utils/
│       ├── yaml.ts           # YAML frontmatter parsing
│       └── markdown.ts       # Markdown processing
└── resources/
    └── agents/               # Built-in agent definitions
```

## package.json Configuration

```json
{
  "name": "ark-orchestrator",
  "displayName": "Ark Agent Orchestrator",
  "description": "Multi-agent orchestration for VS Code Copilot",
  "version": "0.1.0",
  "engines": {
    "vscode": "^1.95.0"
  },
  "categories": ["AI", "Chat"],
  "activationEvents": [
    "onStartupFinished",
    "onChatParticipant:ark"
  ],
  "main": "./dist/extension.js",
  "contributes": {
    "chatParticipants": [
      {
        "id": "ark",
        "name": "Ark",
        "fullName": "Ark Orchestrator",
        "description": "Coordinates multiple agents for complex tasks",
        "isSticky": true,
        "commands": [
          {
            "name": "workflow",
            "description": "Execute a multi-agent workflow"
          },
          {
            "name": "agents",
            "description": "List available agents"
          },
          {
            "name": "delegate",
            "description": "Delegate to a specific agent"
          }
        ]
      }
    ],
    "configuration": {
      "title": "Ark Orchestrator",
      "properties": {
        "ark.agentsFolder": {
          "type": "string",
          "default": ".github/agents",
          "description": "Path to custom agents folder"
        },
        "ark.mcpServers": {
          "type": "object",
          "default": {},
          "description": "MCP server configurations"
        },
        "ark.defaultModel": {
          "type": "string",
          "default": "copilot",
          "description": "Default language model to use"
        }
      }
    },
    "commands": [
      {
        "command": "ark.reloadAgents",
        "title": "Ark: Reload Agents"
      },
      {
        "command": "ark.showAgents",
        "title": "Ark: Show Available Agents"
      }
    ]
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^0.5.0"
  }
}
```

## Core Implementation

### Extension Entry Point

```typescript
// src/extension.ts
import * as vscode from 'vscode';
import { ArkParticipant } from './participant/arkParticipant';
import { AgentLoader } from './agents/agentLoader';
import { McpClient } from './mcp/mcpClient';
import { ToolRegistry } from './tools/toolRegistry';
import { Orchestrator } from './orchestration/orchestrator';

export async function activate(context: vscode.ExtensionContext) {
  console.log('Ark Orchestrator activating...');

  // Initialize components
  const agentLoader = new AgentLoader(context);
  const mcpClient = new McpClient(context);
  const toolRegistry = new ToolRegistry();
  const orchestrator = new Orchestrator(agentLoader, mcpClient, toolRegistry);

  // Load agents from .github/agents/
  await agentLoader.loadAgents();

  // Initialize MCP connections
  await mcpClient.initialize();

  // Register VS Code tools
  toolRegistry.registerVSCodeTools();

  // Register MCP tools
  const mcpTools = await mcpClient.getTools();
  toolRegistry.registerMcpTools(mcpTools);

  // Create chat participant
  const participant = new ArkParticipant(orchestrator);
  
  // Register chat participant
  const disposable = vscode.chat.createChatParticipant('ark', participant.handler);
  
  // Configure participant
  disposable.iconPath = vscode.Uri.joinPath(context.extensionUri, 'resources', 'ark-icon.svg');
  disposable.followupProvider = participant.followupProvider;

  // Register custom agents as additional participants dynamically
  await registerCustomAgentParticipants(context, agentLoader, orchestrator);

  // Watch for agent changes
  agentLoader.onDidChangeAgents(async () => {
    await registerCustomAgentParticipants(context, agentLoader, orchestrator);
  });

  // Register commands
  context.subscriptions.push(
    vscode.commands.registerCommand('ark.reloadAgents', async () => {
      await agentLoader.loadAgents();
      vscode.window.showInformationMessage('Agents reloaded');
    }),
    vscode.commands.registerCommand('ark.showAgents', () => {
      const agents = agentLoader.getAgents();
      // Show quick pick with agents
    }),
    disposable
  );

  console.log('Ark Orchestrator activated');
}

async function registerCustomAgentParticipants(
  context: vscode.ExtensionContext,
  agentLoader: AgentLoader,
  orchestrator: Orchestrator
) {
  // Custom agents are registered through VS Code's native .github/agents/ discovery
  // This function sets up the orchestrator to handle them
  const agents = agentLoader.getAgents();
  
  for (const agent of agents) {
    orchestrator.registerAgent(agent);
  }
}
```

### Chat Participant Implementation

```typescript
// src/participant/arkParticipant.ts
import * as vscode from 'vscode';
import { Orchestrator } from '../orchestration/orchestrator';

export class ArkParticipant {
  constructor(private orchestrator: Orchestrator) {}

  handler: vscode.ChatRequestHandler = async (
    request: vscode.ChatRequest,
    context: vscode.ChatContext,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken
  ): Promise<vscode.ChatResult> => {
    const { prompt, command, references } = request;

    try {
      // Handle slash commands
      if (command) {
        return await this.handleCommand(command, prompt, stream, token);
      }

      // Get current mode/agent context
      const currentAgent = this.getCurrentAgent(context);

      // Gather file context from references
      const fileContext = await this.gatherFileContext(references);

      // Execute through orchestrator
      const result = await this.orchestrator.execute({
        prompt,
        agent: currentAgent,
        context: {
          files: fileContext,
          history: context.history,
          variables: request.variables
        },
        stream,
        token
      });

      // Stream response
      for await (const chunk of result.response) {
        stream.markdown(chunk);
      }

      // Handle follow-up actions
      if (result.followupActions) {
        for (const action of result.followupActions) {
          stream.button({
            command: action.command,
            title: action.title,
            arguments: action.arguments
          });
        }
      }

      return {
        metadata: {
          agentUsed: result.agentUsed,
          toolsUsed: result.toolsUsed
        }
      };
    } catch (error) {
      stream.markdown(`❌ Error: ${error.message}`);
      return { errorDetails: { message: error.message } };
    }
  };

  followupProvider: vscode.ChatFollowupProvider = {
    provideFollowups: async (
      result: vscode.ChatResult,
      context: vscode.ChatContext,
      token: vscode.CancellationToken
    ): Promise<vscode.ChatFollowup[]> => {
      const followups: vscode.ChatFollowup[] = [];
      
      // Suggest agent handoffs based on result
      const handoffs = await this.orchestrator.suggestHandoffs(result, context);
      
      for (const handoff of handoffs) {
        followups.push({
          prompt: handoff.prompt,
          label: handoff.label,
          command: handoff.agent
        });
      }

      return followups;
    }
  };

  private async handleCommand(
    command: string,
    prompt: string,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken
  ): Promise<vscode.ChatResult> {
    switch (command) {
      case 'workflow':
        return this.handleWorkflowCommand(prompt, stream, token);
      case 'agents':
        return this.handleAgentsCommand(stream);
      case 'delegate':
        return this.handleDelegateCommand(prompt, stream, token);
      default:
        stream.markdown(`Unknown command: ${command}`);
        return {};
    }
  }

  private async handleWorkflowCommand(
    prompt: string,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken
  ): Promise<vscode.ChatResult> {
    stream.markdown('🚀 **Starting workflow execution**\n\n');
    
    const result = await this.orchestrator.executeWorkflow(prompt, stream, token);
    
    return {
      metadata: { workflow: true, steps: result.steps }
    };
  }

  private async handleAgentsCommand(
    stream: vscode.ChatResponseStream
  ): Promise<vscode.ChatResult> {
    const agents = this.orchestrator.getAgents();
    
    stream.markdown('# Available Agents\n\n');
    
    for (const agent of agents) {
      stream.markdown(`## ${agent.name}\n`);
      stream.markdown(`${agent.description}\n\n`);
      if (agent.tools.length > 0) {
        stream.markdown(`**Tools**: ${agent.tools.join(', ')}\n\n`);
      }
    }

    return {};
  }

  private async handleDelegateCommand(
    prompt: string,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken
  ): Promise<vscode.ChatResult> {
    // Parse agent name from prompt (e.g., "code-reviewer review this file")
    const [agentName, ...rest] = prompt.split(' ');
    const task = rest.join(' ');

    stream.markdown(`📋 Delegating to **${agentName}**...\n\n`);

    const result = await this.orchestrator.delegateToAgent(agentName, task, stream, token);

    return {
      metadata: { delegated: true, agent: agentName }
    };
  }

  private getCurrentAgent(context: vscode.ChatContext): string | undefined {
    // Get current agent from context if set
    // This integrates with VS Code's mode picker
    return context.history[0]?.participant;
  }

  private async gatherFileContext(
    references: readonly vscode.ChatPromptReference[]
  ): Promise<Array<{ uri: vscode.Uri; content: string }>> {
    const files: Array<{ uri: vscode.Uri; content: string }> = [];

    for (const ref of references) {
      if (ref.value instanceof vscode.Uri) {
        try {
          const content = await vscode.workspace.fs.readFile(ref.value);
          files.push({
            uri: ref.value,
            content: new TextDecoder().decode(content)
          });
        } catch {
          // Skip unreadable files
        }
      }
    }

    return files;
  }
}
```

### Agent Loader

```typescript
// src/agents/agentLoader.ts
import * as vscode from 'vscode';
import * as path from 'path';

export interface ParsedAgent {
  name: string;
  description: string;
  tools: string[];
  systemPrompt: string;
  uri: vscode.Uri;
  mcpServers?: Array<{ name: string; config?: Record<string, unknown> }>;
  handoffs?: Array<{ agent: string; label: string; prompt: string }>;
  argumentHint?: string;
  target?: 'github-copilot' | 'vscode';
  infer?: boolean;
}

export class AgentLoader {
  private agents: Map<string, ParsedAgent> = new Map();
  private _onDidChangeAgents = new vscode.EventEmitter<void>();
  readonly onDidChangeAgents = this._onDidChangeAgents.event;
  private watcher?: vscode.FileSystemWatcher;

  constructor(private context: vscode.ExtensionContext) {}

  async loadAgents(): Promise<void> {
    this.agents.clear();

    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) return;

    for (const folder of workspaceFolders) {
      const agentsDir = vscode.Uri.joinPath(folder.uri, '.github', 'agents');
      
      try {
        const entries = await vscode.workspace.fs.readDirectory(agentsDir);
        
        for (const [name, type] of entries) {
          if (type !== vscode.FileType.File) continue;
          if (!name.endsWith('.md')) continue;
          if (name.toLowerCase() === 'readme.md') continue;

          const uri = vscode.Uri.joinPath(agentsDir, name);
          const agent = await this.parseAgentFile(uri);
          
          if (agent) {
            this.agents.set(agent.name, agent);
          }
        }
      } catch {
        // Agents folder doesn't exist
      }
    }

    // Set up file watcher
    this.setupWatcher();
    
    this._onDidChangeAgents.fire();
  }

  private setupWatcher(): void {
    if (this.watcher) {
      this.watcher.dispose();
    }

    this.watcher = vscode.workspace.createFileSystemWatcher(
      '**/.github/agents/*.md'
    );

    const reload = () => this.loadAgents();
    this.watcher.onDidCreate(reload);
    this.watcher.onDidChange(reload);
    this.watcher.onDidDelete(reload);

    this.context.subscriptions.push(this.watcher);
  }

  private async parseAgentFile(uri: vscode.Uri): Promise<ParsedAgent | undefined> {
    try {
      const content = await vscode.workspace.fs.readFile(uri);
      const text = new TextDecoder().decode(content);

      // Parse YAML frontmatter
      const frontmatterMatch = text.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
      const body = frontmatterMatch 
        ? text.slice(frontmatterMatch[0].length).trim()
        : text.trim();

      const header = frontmatterMatch 
        ? this.parseYaml(frontmatterMatch[1])
        : {};

      const name = header.name || path.basename(uri.path)
        .replace(/\.agent\.md$/, '')
        .replace(/\.md$/, '');

      return {
        name,
        description: header.description || '',
        tools: this.parseTools(header.tools),
        systemPrompt: body,
        uri,
        mcpServers: header['mcp-servers'],
        handoffs: header.handoffs,
        argumentHint: header.argumentHint,
        target: header.target,
        infer: header.infer
      };
    } catch (error) {
      console.error(`Failed to parse agent file: ${uri}`, error);
      return undefined;
    }
  }

  private parseYaml(yaml: string): Record<string, any> {
    // Simplified YAML parsing - in production use a proper YAML parser
    const result: Record<string, any> = {};
    // ... implementation similar to bridge.ts
    return result;
  }

  private parseTools(tools: any): string[] {
    if (!tools) return [];
    if (Array.isArray(tools)) return tools.map(String);
    if (typeof tools === 'string') {
      const match = tools.match(/\[(.*?)\]/);
      if (match) {
        return match[1].split(',').map(t => t.trim().replace(/['"]/g, ''));
      }
    }
    return [];
  }

  getAgents(): ParsedAgent[] {
    return Array.from(this.agents.values());
  }

  getAgent(name: string): ParsedAgent | undefined {
    return this.agents.get(name);
  }

  dispose(): void {
    this.watcher?.dispose();
    this._onDidChangeAgents.dispose();
  }
}
```

### MCP Integration

```typescript
// src/mcp/mcpClient.ts
import * as vscode from 'vscode';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

export interface McpTool {
  name: string;
  description?: string;
  inputSchema?: object;
  server: string;
}

export class McpClient {
  private clients: Map<string, Client> = new Map();
  private tools: McpTool[] = [];

  constructor(private context: vscode.ExtensionContext) {}

  async initialize(): Promise<void> {
    const config = vscode.workspace.getConfiguration('ark');
    const mcpServers = config.get<Record<string, any>>('mcpServers', {});

    for (const [name, serverConfig] of Object.entries(mcpServers)) {
      try {
        const client = await this.connectToServer(name, serverConfig);
        this.clients.set(name, client);
        
        // Get tools from this server
        const serverTools = await this.discoverTools(client, name);
        this.tools.push(...serverTools);
      } catch (error) {
        console.error(`Failed to connect to MCP server: ${name}`, error);
      }
    }
  }

  private async connectToServer(name: string, config: any): Promise<Client> {
    const transport = new StdioClientTransport({
      command: config.command,
      args: config.args || [],
      env: config.env
    });

    const client = new Client({
      name: `ark-${name}`,
      version: '1.0.0'
    });

    await client.connect(transport);
    return client;
  }

  private async discoverTools(client: Client, serverName: string): Promise<McpTool[]> {
    const { tools } = await client.listTools();
    
    return tools.map(tool => ({
      name: `${serverName}_${tool.name}`,
      description: tool.description,
      inputSchema: tool.inputSchema,
      server: serverName
    }));
  }

  async getTools(): Promise<McpTool[]> {
    return this.tools;
  }

  async callTool(
    serverName: string,
    toolName: string,
    args: Record<string, unknown>
  ): Promise<unknown> {
    const client = this.clients.get(serverName);
    if (!client) {
      throw new Error(`MCP server not connected: ${serverName}`);
    }

    const result = await client.callTool({
      name: toolName,
      arguments: args
    });

    return result.content;
  }

  dispose(): void {
    for (const client of this.clients.values()) {
      client.close();
    }
    this.clients.clear();
  }
}
```

### Tool Registry

```typescript
// src/tools/toolRegistry.ts
import * as vscode from 'vscode';
import { McpTool } from '../mcp/mcpClient';

export interface Tool {
  name: string;
  description: string;
  execute: (args: Record<string, unknown>) => Promise<unknown>;
}

export class ToolRegistry {
  private tools: Map<string, Tool> = new Map();

  registerVSCodeTools(): void {
    // Register built-in VS Code tools
    this.register({
      name: 'readFile',
      description: 'Read file contents',
      execute: async (args) => {
        const uri = vscode.Uri.file(args.path as string);
        const content = await vscode.workspace.fs.readFile(uri);
        return new TextDecoder().decode(content);
      }
    });

    this.register({
      name: 'editFile',
      description: 'Edit file contents',
      execute: async (args) => {
        const uri = vscode.Uri.file(args.path as string);
        const edit = new vscode.WorkspaceEdit();
        // ... apply edits
        await vscode.workspace.applyEdit(edit);
        return { success: true };
      }
    });

    this.register({
      name: 'createFile',
      description: 'Create a new file',
      execute: async (args) => {
        const uri = vscode.Uri.file(args.path as string);
        await vscode.workspace.fs.writeFile(
          uri,
          new TextEncoder().encode(args.content as string)
        );
        return { success: true, path: args.path };
      }
    });

    this.register({
      name: 'search',
      description: 'Search files in workspace',
      execute: async (args) => {
        const results = await vscode.workspace.findFiles(
          args.pattern as string,
          args.exclude as string
        );
        return results.map(uri => uri.fsPath);
      }
    });

    this.register({
      name: 'runTerminalCommand',
      description: 'Run a command in the terminal',
      execute: async (args) => {
        const terminal = vscode.window.createTerminal('Ark');
        terminal.sendText(args.command as string);
        terminal.show();
        return { success: true };
      }
    });

    this.register({
      name: 'runSubagent',
      description: 'Run a sub-agent',
      execute: async (args) => {
        // This is handled specially by the orchestrator
        return { subagent: args.agent, prompt: args.prompt };
      }
    });
  }

  registerMcpTools(mcpTools: McpTool[]): void {
    for (const tool of mcpTools) {
      this.register({
        name: tool.name,
        description: tool.description || '',
        execute: async (args) => {
          // Execution is delegated to MCP client
          return { __mcp__: true, server: tool.server, name: tool.name, args };
        }
      });
    }
  }

  register(tool: Tool): void {
    this.tools.set(tool.name, tool);
  }

  get(name: string): Tool | undefined {
    return this.tools.get(name);
  }

  list(): Tool[] {
    return Array.from(this.tools.values());
  }
}
```

## Integration with VS Code's Native Agent System

The extension works alongside VS Code's native agent discovery:

1. **VS Code discovers agents** from `.github/agents/` folder automatically
2. **Ark extension loads same agents** and adds orchestration capabilities  
3. **Users select agents** from the mode picker
4. **Ark orchestrator** handles complex multi-agent workflows

### Native VS Code Agent Discovery

VS Code automatically:
- Scans `.github/agents/*.agent.md` and `.github/agents/*.md`
- Parses YAML frontmatter
- Registers agents in the mode picker
- Provides `modeInstructions` to the chat request

### Ark Extension Enhancement

Ark adds:
- Multi-agent orchestration via `runSubagent` tool
- MCP server integration
- Conversation persistence
- Workflow execution
- Cross-agent coordination

## Configuration

### VS Code Settings

```json
{
  "ark.agentsFolder": ".github/agents",
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
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "${workspaceFolder}"]
    }
  },
  "ark.defaultModel": "copilot"
}
```

### MCP Server Configuration

MCP servers can be configured:

1. **Globally in settings.json** (ark.mcpServers)
2. **Per-agent in .agent.md** (mcp-servers field)
3. **Via VS Code's native MCP support** (when available)

## Workflow Execution

```
User: @ark /workflow Create a new user authentication feature

Ark Orchestrator:
  1. Analyze request
  2. Break down into sub-tasks
  3. Delegate to PM Breakdown agent
  4. Receive feature specification
  5. Delegate to Implementation agent
  6. Receive code changes
  7. Delegate to Code Reviewer agent
  8. Receive review feedback
  9. Apply fixes if needed
  10. Delegate to Documentation agent
  11. Generate docs
  12. Present final result
```

## Next Steps

1. Create the extension scaffold
2. Implement core components
3. Test with sample agents
4. Add MCP server support
5. Build workflow engine
6. Create distribution package
