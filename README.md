---
title: README.md
description: Projektübersicht für Substrate AI – Features, Architektur und Einstieg.
created: 2026-01-01
updated: 2026-08-28
---

# Substrate AI

**Production-ready AI agent framework** with streaming, memory, tools, and MCP integration.

Built on OpenRouter, PostgreSQL persistence, and an extensible tool architecture.

---

## Quick Start

```bash
git clone https://github.com/Duzafizzl/substrate-ai.git
cd substrate-ai
python setup.py          # venv, deps, config
# OPENROUTER_API_KEY in backend/.env eintragen
./start.sh               # oder Backend + Frontend manuell starten
```

→ Browser: **http://localhost:5173**

Details, Troubleshooting und manuelles Setup: **[QUICK_START.md](QUICK_START.md)**

Optional: vorkonfigurierter **ALEX**-Agent nach API-Key-Setup:

```bash
cd backend && source venv/bin/activate && python setup_alex.py
```

---

## Features

| Bereich | Highlights |
|---------|------------|
| **Core** | Multi-Model (OpenRouter), SSE-Streaming, Sessions, Cost Tracking |
| **Memory** | Core + Archival (ChromaDB), Miras-Architektur (Retention, Attention, Hierarchie) |
| **Tools** | Web, Search, Discord, Code-Sandbox, Graph RAG |
| **MCP** | Browser-Automation (Playwright), Vision (Gemini), Skills |
| **Autonomous** | Heartbeat, Rooms/Channels, Task Scheduler, Daemon Mode |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Frontend (React + Vite)             │
│  Streaming UI · Sessions · Memory · Rooms        │
└─────────────────┬───────────────────────────────┘
                  │ HTTP / SSE
┌─────────────────▼───────────────────────────────┐
│           Backend (Python / Flask)               │
│  Consciousness Loop · Daemon · Tools · MCP       │
│  Memory (Miras) · Channels · Task Scheduler        │
└──────────────────┬──────────────────────────────┘
                   │
     ┌─────────────┼─────────────┬─────────────┐
     │             │             │             │
 PostgreSQL    ChromaDB    MCP Servers    Neo4j (opt.)
```

---

## Tech Stack

**Backend:** Python 3.11+, Flask, PostgreSQL, ChromaDB, OpenRouter, RestrictedPython  
**Frontend:** React 18, TypeScript, Tailwind, Vite  
**MCP:** Playwright, Gemini Flash, fastmcp

---

## Documentation

| Thema | Datei |
|-------|-------|
| Setup & Start | [QUICK_START.md](QUICK_START.md) |
| Projektstruktur | [STRUCTURE.txt](STRUCTURE.txt) |
| MCP-System | [MCP_SYSTEM_OVERVIEW.md](MCP_SYSTEM_OVERVIEW.md) |
| Miras Memory | [docs/MIRAS_TITANS_INTEGRATION.md](docs/MIRAS_TITANS_INTEGRATION.md) |
| Beispiel-Agents | [examples/README.md](examples/README.md) |
| PostgreSQL | [backend/POSTGRESQL_SETUP.md](backend/POSTGRESQL_SETUP.md) |
| Python 3.13 | [backend/PYTHON_3.13_COMPATIBILITY.md](backend/PYTHON_3.13_COMPATIBILITY.md) |

---

## API Overview

REST endpoints for agents, chat (SSE), memory, graph RAG, channels, tasks, and heartbeat.  
Full endpoint lists and tool reference: see source in `backend/api/` and [MCP_SYSTEM_OVERVIEW.md](MCP_SYSTEM_OVERVIEW.md).

---

## Security

Sandboxed code execution, domain whitelisting for browser automation, rate limiting, CORS, input sanitization.  
Details: `backend/` security modules and config in `.env`.

---

## Development

```bash
# Backend
cd backend && source venv/bin/activate && python api/server.py

# Frontend
cd frontend && npm install && npm run dev
```

```bash
cd backend && python test_startup.py
cd frontend && npm run build
```

---

## Contributing

Fork → feature branch → tests → pull request.  
Python: PEP 8, type hints. TypeScript: ESLint, strict mode.

---

## License

See [LICENSE](LICENSE).

---

*Version 1.2.1 · Updated: August 2026*
