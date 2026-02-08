# Second Brain Kit

> One-click setup for your AI-powered second brain. Obsidian + Claude Code + Discord, packaged for everyone.

## Problem

AI conversations disappear after every session. Notes pile up but never get organized. Knowledge workers drown in information they can't retrieve when needed.

Meanwhile, powerful workflows exist (Obsidian vault + Claude AI + Discord) that solve this — but they require hours of technical setup that only developers can handle.

## Solution

**Second Brain Kit** packages the entire "AI second brain" workflow into a one-click installer:

- **Your data, your machine** — Everything stored as local Markdown files. No vendor lock-in.
- **AI that organizes for you** — Chat naturally, and AI auto-tags, categorizes, and links your knowledge.
- **Discord as your interface** — Talk to your second brain from anywhere, anytime.
- **MCP Store** — Install integrations (Calendar, Todoist, RSS, etc.) with a single click.

## How It Works

```
You (Discord) ←→ Second Brain Kit ←→ Your Knowledge Vault
                      │
                      ├── Claude Code CLI (AI reasoning)
                      ├── Obsidian Vault (local Markdown)
                      ├── MCP Servers (integrations)
                      └── Auto-tagging & organization
```

1. **Install** — Run the installer. It sets up Obsidian, vault structure, and Discord bot automatically.
2. **Connect** — Set up your Claude Code subscription and Discord server.
3. **Chat** — Talk to your AI second brain via Discord. It remembers everything.
4. **Browse** — Open Obsidian anytime to see your beautifully organized knowledge base.

## Tech Stack

- **Language**: Python 3.11+
- **Discord**: discord.py
- **AI**: Claude Code CLI (`claude -p` subprocess)
- **Knowledge Base**: Obsidian (Markdown files)
- **Integrations**: MCP (Model Context Protocol) servers

## Quick Start

```bash
# Clone the repo
git clone https://github.com/JunsikChoi/second-brain-kit.git
cd second-brain-kit

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your Discord token, owner ID, and vault path

# Run
second-brain-kit
```

### Prerequisites

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- Discord bot token ([guide](https://discord.com/developers/applications))
- Obsidian vault directory

## Discord Commands

| Command | Description |
|---------|-------------|
| `/new` | Start a new session |
| `/model` | Change Claude model (sonnet/opus/haiku) |
| `/status` | Current session info |
| `/system` | Set or view system prompt |
| `/export` | Export conversation history |
| `/search` | Search vault notes (filename, tags, body) |
| `/notes` | List recent notes in vault |
| `/tags` | Show all tags in vault |
| `/save` | Save a note to vault with title, content, tags |
| `/autotag` | Auto-tag a note using AI |
| `/mcp list` | List available MCP servers with install status |
| `/mcp install` | Install an MCP server (Google Calendar, Todoist, RSS) |
| `/mcp remove` | Remove an installed MCP server |
| `/mcp status` | Show installed MCP server status |
| `/cost` | Show total cost (admin) |
| `/sessions` | List active sessions (admin) |
| `/kill` | Kill running Claude processes (admin) |
| `/budget` | Set per-turn budget (admin) |

## Roadmap

- [ ] **Phase 1: MVP** — Discord bot + vault manager + MCP manager + CLI installer
- [ ] **Phase 2: Polish** — GUI installer, cross-platform, semantic search
- [ ] **Phase 3: Community** — MCP marketplace, vault templates, mobile companion

## Contributing

This is an open-source project. Contributions welcome!

## License

MIT
