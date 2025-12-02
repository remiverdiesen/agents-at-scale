# Ark-Lite VS Code Integration Summary

## ✅ Completed Work

This document summarizes the VS Code integration work completed for Ark-Lite, aligning with VS Code's native Copilot Chat agent system.

### 1. Agent Format Alignment

**Issue Identified**: The original implementation used a non-standard `chatagent` code block format:
```markdown
```chatagent
---
name: 'Agent'
---
```
```

**Fixed to VS Code Standard**: Now uses proper YAML frontmatter format:
```markdown
---
name: 'Agent'
description: 'What this agent does'
tools: ['readFile', 'editFile']
---

Agent instructions here...
```

### 2. Files Created/Modified

#### New Agent Definitions (`.github/agents/`)

| File | Purpose |
|------|---------|
| [README.md](.github/agents/README.md) | Complete agent format documentation |
| [orchestrator.agent.md](.github/agents/orchestrator.agent.md) | Main orchestrator for multi-agent workflows |
| [pm-breakdown.agent.md](.github/agents/pm-breakdown.agent.md) | Product management decomposition agent |
| [code-reviewer.agent.md](.github/agents/code-reviewer.agent.md) | Code review and quality analysis agent |
| [documentation.agent.md](.github/agents/documentation.agent.md) | Technical documentation generator |
| [implementation.agent.md](.github/agents/implementation.agent.md) | Code implementation agent |

#### Updated Core Files

| File | Changes |
|------|---------|
| [ark/src/vscode/bridge.ts](ark/src/vscode/bridge.ts) | Fixed YAML parsing to match VS Code format |
| [ark/src/types/agent.ts](ark/src/types/agent.ts) | Added handoffs, mcpServers, argumentHint, target, infer fields |

#### New Documentation

| File | Content |
|------|---------|
| [docs/VSCODE_EXTENSION_ARCHITECTURE.md](docs/VSCODE_EXTENSION_ARCHITECTURE.md) | Complete VS Code extension architecture |
| [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md) | MCP protocol integration strategy |

### 3. VS Code Agent Format Specification

Agents in `.github/agents/` support these YAML frontmatter fields:

```yaml
---
# Required
name: 'Agent Name'                              # Display name
description: 'What this agent does'             # Shown in picker

# Optional - Tools
tools: ['readFile', 'editFile', 'search']       # Available tools

# Optional - MCP Integration
mcp-servers:                                     # MCP servers to connect
  - name: 'github'
  - name: 'filesystem'
    config:
      rootPath: '${workspaceFolder}'

# Optional - Agent Handoffs
handoffs:                                        # Transition to other agents
  - agent: 'Edit'
    label: 'Make changes'
    prompt: 'Implement the discussed changes'

# Optional - Metadata
model: 'gpt-4o'                                 # Model preference
argumentHint: 'Describe what to build'          # UI hint
target: 'vscode'                                # Platform target
infer: true                                     # Allow as sub-agent
---

Agent instructions (markdown body)...
```

### 4. Tool References

Tools can be referenced in the agent body using the `#tool:toolname` syntax:

```markdown
When editing files, use #tool:editFile to make changes.
Use #tool:search to find relevant code.
```

This is automatically parsed and tracked for VS Code integration.

### 5. Supported Tools

| Tool | Description |
|------|-------------|
| `readFile` | Read file contents |
| `editFile` | Edit existing files |
| `createFile` | Create new files |
| `createDirectory` | Create directories |
| `search` | Search files and content |
| `runTerminalCommand` | Execute shell commands |
| `runSubagent` | Delegate to another agent |
| `todo` | Create and manage todo items |

Plus any tools from connected MCP servers.

### 6. Key Architecture Decisions

1. **VS Code as Orchestrator**: The VS Code extension serves as the central orchestrator for multi-agent workflows
2. **Native Agent Discovery**: Leverages VS Code's built-in `.github/agents/` folder scanning
3. **MCP Integration**: Connects to MCP servers for extended tool capabilities
4. **Dual Execution**: Supports both CLI and VS Code Copilot Chat execution
5. **CRD Compatibility**: Converts agents to Kubernetes CRD-style resources for backend processing

### 7. Integration Points

```
┌─────────────────────────────────────────────────┐
│              VS Code Copilot Chat               │
│  ┌───────────────────────────────────────────┐  │
│  │         Mode Picker (Agent Select)        │  │
│  │  [Ask] [Agent ▼] [Orchestrator] [PM]...   │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────┘
                      │
         ┌────────────▼────────────┐
         │   .github/agents/*.md   │
         │   (Agent Definitions)   │
         └────────────┬────────────┘
                      │
         ┌────────────▼────────────┐
         │     Ark-Lite Bridge     │
         │   (bridge.ts parser)    │
         └────────────┬────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────┐    ┌───────────┐    ┌─────────────┐
│ VS Code │    │    MCP    │    │ Orchestrator│
│  Tools  │    │  Servers  │    │    Core     │
└─────────┘    └───────────┘    └─────────────┘
```

### 8. Next Steps

1. **Create VS Code Extension Package**
   - Scaffold extension with `yo code`
   - Implement chat participant
   - Register tools with VS Code

2. **Implement MCP Client**
   - Connect to MCP servers
   - Discover and register tools
   - Handle tool execution

3. **Build Orchestration Logic**
   - Multi-agent workflow execution
   - Session management
   - Conversation persistence

4. **Testing**
   - Unit tests for parser
   - Integration tests with VS Code
   - E2E workflow tests

### 9. Usage

#### In VS Code Copilot Chat:
```
# Select agent from mode picker, then:
@orchestrator Create a new user authentication feature

# Or use slash commands:
@ark /workflow Create authentication
@ark /delegate code-reviewer Review the auth module
@ark /agents List available agents
```

#### Via CLI:
```bash
npm run cli -- query agent orchestrator "Create a new feature"
npm run cli -- workflow run --agents pm-breakdown,implementation
```

### 10. Configuration

#### VS Code Settings (settings.json):
```json
{
  "chat.useAgentsMdFile": true,
  "chat.useNestedAgentMdFile": true,
  "ark.agentsFolder": ".github/agents",
  "ark.mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "${env:GITHUB_TOKEN}" }
    }
  }
}
```

## Verification

The implementation has been verified against VS Code's source code:
- ✅ YAML frontmatter format matches VS Code's `promptValidator.test.ts`
- ✅ Supported fields align with `ICustomAgent` interface
- ✅ Tool references use `#tool:toolname` syntax
- ✅ Agent discovery matches `.github/agents/` folder pattern
- ✅ MCP integration follows `mcpLanguageModelToolContribution.ts` pattern

## References

- [VS Code Chat Agent Source](https://github.com/microsoft/vscode/tree/main/src/vs/workbench/contrib/chat)
- [VS Code Prompt Syntax](https://github.com/microsoft/vscode/tree/main/src/vs/workbench/contrib/chat/common/promptSyntax)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [VS Code Language Model API](https://code.visualstudio.com/api/extension-guides/language-model)
