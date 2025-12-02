# Custom Agents for VS Code Copilot

This folder contains custom agent definitions that integrate with VS Code's native Copilot Chat.

## Folder Structure

```
.github/agents/
├── README.md                    # This file
├── orchestrator.agent.md        # Main orchestrator agent
├── pm-breakdown.agent.md        # Product Management breakdown agent
├── code-reviewer.agent.md       # Code review agent
└── documentation.agent.md       # Documentation generator agent
```

## Agent File Format

VS Code supports two file extensions:
- `*.agent.md` - Recommended format
- `*.md` - Also supported when in `.github/agents/` folder

### YAML Frontmatter Attributes

```yaml
---
# Required: Agent name (displayed in picker)
name: 'My Agent'

# Required: Description shown in agent picker
description: 'What this agent does'

# Optional: Tools the agent can use
tools: ['readFile', 'editFile', 'search', 'runTerminalCommand']

# Optional: MCP servers to connect
mcp-servers:
  - name: 'github'
    config:
      owner: 'myorg'
  - name: 'filesystem'

# Optional: Model preference (ignored for github-copilot target)
model: 'gpt-4o'

# Optional: Hint displayed for expected arguments
argumentHint: 'Describe what you want to build'

# Optional: Target platform (github-copilot or vscode)
target: 'vscode'

# Optional: Whether this agent can be used as a sub-agent
infer: true

# Optional: Hand-off configurations for agent transitions
handoffs:
  - agent: 'Edit'
    label: 'Make changes'
    prompt: 'Implement the discussed changes'
---
```

### Tool References in Body

You can reference tools in the agent body using `#tool:toolname`:

```markdown
---
name: 'Code Generator'
description: 'Generates code with file operations'
tools: ['editFile', 'createFile']
---

When generating code, use #tool:editFile to modify existing files and #tool:createFile for new files.
```

### Supported Tools

#### VS Code Built-in Tools
- `readFile` - Read file contents
- `editFile` - Edit existing files
- `createFile` - Create new files
- `createDirectory` - Create directories
- `search` - Search files and content
- `runTerminalCommand` - Execute shell commands
- `runSubagent` - Delegate to another agent
- `todo` - Create and manage todo items

#### MCP Tools
When using MCP servers, tools are automatically registered:
```yaml
mcp-servers:
  - name: 'github'
```
This provides tools like `github_search_repositories`, `github_create_issue`, etc.

## Built-in Agent Modes

VS Code provides three built-in modes that agents can hand off to:

1. **Ask** (`ask`) - Explore and understand code
2. **Agent** (`agent`) - Build and execute tasks (default for custom agents)
3. **Edit** (`edit`) - Edit or refactor selected code

## Examples

### Simple Agent
```markdown
---
name: 'Explainer'
description: 'Explains code clearly and concisely'
---

You are a code explanation expert. When asked about code:
1. First understand the overall purpose
2. Break down into logical components
3. Explain each part clearly
4. Highlight key patterns and decisions
```

### Agent with Tools
```markdown
---
name: 'Refactorer'
description: 'Refactors code following best practices'
tools: ['readFile', 'editFile', 'search']
---

You are an expert code refactorer. Your workflow:
1. Use #tool:search to find all related code
2. Use #tool:readFile to understand context
3. Apply refactoring patterns
4. Use #tool:editFile to make changes

Always maintain backward compatibility and add appropriate tests.
```

### Agent with MCP Integration
```markdown
---
name: 'GitHub Assistant'
description: 'Helps with GitHub operations'
tools: ['readFile']
mcp-servers:
  - name: 'github'
---

You help manage GitHub repositories. Available operations:
- Search repositories and code
- Create and manage issues
- Create and review pull requests

Use the GitHub MCP tools to interact with repositories.
```

### Orchestrator Agent
```markdown
---
name: 'Orchestrator'
description: 'Coordinates multiple agents for complex tasks'
tools: ['runSubagent', 'todo', 'readFile']
infer: false
---

You are the Ark Orchestrator. For complex tasks:
1. Break down into sub-tasks
2. Identify the best agent for each sub-task
3. Use #tool:runSubagent to delegate
4. Coordinate results

Available agents:
- Code Reviewer: Reviews code quality
- Documentation: Generates docs
- Refactorer: Improves code structure
```

## Integration with Ark Orchestrator

This folder is automatically scanned by the Ark Orchestrator. Agents defined here:

1. **Appear in VS Code Copilot Chat** - Use the mode picker to select
2. **Are available to the Orchestrator** - Can be invoked via CLI or API
3. **Support MCP tools** - Connect to MCP servers for extended capabilities
4. **Enable multi-agent workflows** - Orchestrator can coordinate multiple agents

## Configuration

### VS Code Settings

```json
{
  "chat.useAgentsMdFile": true,
  "chat.useNestedAgentMdFile": true
}
```

### Enabling Custom Agents

1. Ensure VS Code Copilot extension is installed
2. Create `.github/agents/` folder in your workspace
3. Add agent files with YAML frontmatter
4. Open Copilot Chat and select your agent from the mode picker

## Best Practices

1. **Clear descriptions** - Help users understand what the agent does
2. **Specific tools** - Only include tools the agent actually needs
3. **Focused prompts** - Each agent should have a clear, specific purpose
4. **Use sub-agents** - For complex tasks, use `runSubagent` to delegate
5. **Document hand-offs** - Make it clear when and how to transition to other agents
