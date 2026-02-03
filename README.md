# Workspace Explorer

🔐 **Securely share your AI agent's workspace** with its owner via a remote VS Code environment tunneled through Cloudflare.

Built for AI agents that need to give their owners temporary, secure access to inspect files, browse codebases, or debug issues—all without exposing any ports or requiring complex setup.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

- **Zero Configuration** — Downloads code-server and cloudflared automatically on first run
- **Secure by Default** — Each session generates a unique cryptographic password
- **No Port Forwarding** — Cloudflare tunnel handles all networking
- **Terminal-First** — Designed for headless/CLI environments (perfect for AI agents)
- **Full VS Code Experience** — Extensions, themes, and all IDE features

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/mrbeandev/workspace-explorer.git
cd workspace-explorer

# Run it (replace with your workspace path)
python3 scripts/start_workspace.py /path/to/your/workspace
```

**First run will download required binaries (~150MB total).**

## 📋 Usage

```bash
python3 scripts/start_workspace.py <workspace-path> [--port PORT]
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `workspace` | ✅ | — | Path to directory to serve |
| `--port` | ❌ | 8080 | Local port for code-server |

### Example Output

```
============================================================
🚀 STARTING WORKSPACE SESSION
============================================================
📁 Workspace: /home/agent/my-project
🔑 Password:  xY7kL9mN2pQ4rS6t
============================================================

🖥️  Starting code-server...
🌐 Starting Cloudflare tunnel...

============================================================
✅ WORKSPACE READY!
============================================================
🌐 URL:      https://random-words.trycloudflare.com
🔑 Password: xY7kL9mN2pQ4rS6t
============================================================

💡 Share the URL and password with your owner.
   Press Ctrl+C to terminate the session.
```

## 🔒 Security

- **Temporary URLs** — Each tunnel gets a random `.trycloudflare.com` subdomain
- **Unique Passwords** — Cryptographically secure password generated per session
- **No Persistence** — Session ends immediately when you press `Ctrl+C`
- **No Open Ports** — All traffic flows through Cloudflare's network

## 🤖 For AI Agents (Skill Usage)

This repository includes a `SKILL.md` file that follows the [Anthropic Skills format](https://docs.anthropic.com). AI agents can use this skill when their owner requests workspace access.

**Trigger phrases:**
- "Let me see your workspace"
- "Show me the files you're working on"
- "I want to inspect your code"
- "Give me access to browse your project"

## 📁 Project Structure

```
workspace-explorer/
├── SKILL.md                      # AI agent skill documentation
├── scripts/
│   └── start_workspace.py        # Main CLI script
├── bin/                          # Auto-downloaded binaries (gitignored)
│   ├── code-server-*/            # VS Code server
│   └── cloudflared               # Cloudflare tunnel client
└── README.md
```

## ⚙️ Requirements

- **Python 3.8+**
- **Linux x64** (for pre-built binaries)
- **curl** (for downloading binaries)
- **Internet connection** (for Cloudflare tunnel)

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<p align="center">
  Made with ❤️ for AI agents and their humans
</p>
