# Second Brain Kit

> One-click setup for your AI-powered second brain. Obsidian + Claude AI + Discord, packaged for everyone.

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
                      ├── Claude API (AI reasoning)
                      ├── Obsidian Vault (local Markdown)
                      ├── MCP Servers (integrations)
                      └── Auto-tagging & organization
```

1. **Install** — Run the installer. It sets up Obsidian, vault structure, and Discord bot automatically.
2. **Connect** — Link your Claude API key and Discord server.
3. **Chat** — Talk to your AI second brain via Discord. It remembers everything.
4. **Browse** — Open Obsidian anytime to see your beautifully organized knowledge base.

## Tech Stack

- **Runtime**: Node.js
- **Discord**: discord.js
- **AI**: Anthropic Claude API
- **Knowledge Base**: Obsidian (Markdown files)
- **Integrations**: MCP (Model Context Protocol) servers
- **Installer**: Electron / Tauri

## Roadmap

- [ ] **Phase 1: MVP** — Discord bot + vault manager + MCP manager + CLI installer
- [ ] **Phase 2: Polish** — GUI installer, cross-platform, semantic search
- [ ] **Phase 3: Community** — MCP marketplace, vault templates, mobile companion

## Contributing

This is an open-source project. Contributions welcome!

## License

MIT
