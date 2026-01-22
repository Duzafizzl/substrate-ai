# Substrate AI

**A production-ready AI agent framework with streaming, memory, tools, and MCP integration.**

Built on modern LLM infrastructure with OpenRouter support, PostgreSQL persistence, and extensible tool architecture.

---

## 🚀 Quick Start (One-Click Setup!)

### Option 1: Automatic Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/substrate-ai.git
cd substrate-ai

# Run the setup wizard - it does EVERYTHING for you!
python setup.py
```

The setup script will:
- ✅ Create Python virtual environment
- ✅ Install all backend dependencies
- ✅ Create configuration files
- ✅ Install frontend dependencies
- ✅ Validate your setup

**After setup, just add your API key:**
```bash
# Edit backend/.env and add your OpenRouter API key
# Get one at: https://openrouter.ai/keys
```

### Option 2: Manual Setup

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install

# Configure
cp backend/.env.example backend/.env
# Edit backend/.env and add OPENROUTER_API_KEY=sk-or-v1-your-key
```

### Start the Application

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
python api/server.py

# Terminal 2: Frontend
cd frontend
npm run dev

# Open http://localhost:5173 🎉
```

📖 **Full guide:** See [QUICK_START.md](QUICK_START.md)

**✨ New users:** The repository includes **ALEX** - a pre-configured example agent. Run `python setup_alex.py` after configuring your API key to get started immediately!

---

## ✨ Features

### Core Capabilities
- 🤖 **Multi-Model Support** - OpenRouter integration with 100+ LLMs
- 💬 **Streaming Responses** - Real-time token streaming with SSE
- 🧠 **Memory System** - Short-term (PostgreSQL) + Long-term (ChromaDB embeddings)
- 🛠️ **Tool Execution** - Extensible tool architecture with built-in tools
- 🔄 **Session Management** - Multi-session support with conversation history
- 💰 **Cost Tracking** - Real-time token usage and cost monitoring
- ⚡ **Token Optimized** - ~40% fewer context tokens via history limits + auto-summarization

### Advanced Features
- 🧩 **MCP Integration** - Model Context Protocol for code execution & browser automation
- 📊 **PostgreSQL Backend** - Scalable conversation & memory persistence
- 🕸️ **Graph RAG** - Knowledge graph retrieval (works without Neo4j - uses local DB fallback!)
- 🎯 **Vision Support** - Gemini Flash integration for image analysis
- 🔐 **Security Hardened** - Sandboxed code execution, rate limiting, domain whitelisting
- 📈 **Token Efficiency** - 98.7% context window savings via MCP code execution
- 🎨 **Modern UI** - React + TypeScript + Tailwind CSS

### 🔄 Autonomous Agent Features (NEW!)
- 💓 **Heartbeat System** - Timer-based agent activation with configurable rules
- 📂 **Rooms/Channels** - Discord-style message organization (heartbeat-log, task, reflection)
- 🗓️ **Task Scheduler** - Automatic task execution (daily, weekly, monthly, custom intervals)
- 🏃 **Daemon Mode** - 24/7 agent runtime with in-memory caching

### 🧠 Miras Memory Architecture
Based on Google Research [Titans/Miras papers](https://research.google/blog/titans-miras-helping-ai-have-long-term-memory/):
- 🔄 **Retention Gates** - Dynamic memory decay/boost based on access patterns
- 👁️ **Attentional Bias** - Multi-factor scoring (semantic + temporal + importance + access)
- 🏛️ **Hierarchical Memory** - 3-tier system (Working → Episodic → Semantic)
- 📈 **Online Learning** - Hebbian associations + feedback learning during runtime

### 💓 Heartbeat & Autonomous Agent System (NEW!)
Always-on agent capabilities for 24/7 autonomous operation:
- **Timer-based Heartbeats** - Configurable rules with time windows & probability
- **Rooms/Channels** - Discord-style message organization with threads
- **Task Scheduler** - Daily, weekly, monthly, or custom interval tasks
- **Daemon Mode** - 24/7 runtime with hot agent caching
- **DST-safe Timezone** - Europe/Berlin default with proper timezone handling

---

## 📚 Documentation

### Getting Started
- **[Quick Start Guide](QUICK_START.md)** - 5-minute setup
- **[System Structure](STRUCTURE.txt)** - Project layout overview
- **[Example Agents](examples/README.md)** - Pre-configured agent templates

### Advanced Topics
- **[MCP System Overview](MCP_SYSTEM_OVERVIEW.md)** - Code execution & browser automation architecture
- **[Miras Memory Architecture](docs/MIRAS_TITANS_INTEGRATION.md)** - Research-backed memory system
- **[Heartbeat & Rooms](IMPLEMENTATION_PLAN_HEARTBEAT_ROOMS.md)** - Autonomous agent features
- **[PostgreSQL Setup](backend/POSTGRESQL_SETUP.md)** - Database configuration
- **[Compatibility Guide](backend/COMPATIBILITY.md)** - System requirements

### Testing & Security
- **[Testing Results](TESTING_RESULTS.md)** - Test coverage & validation
- **[Security Checklist](FINAL_SECURITY_CHECK.md)** - Security audit & hardening

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│              Frontend (React)                    │
│  • Real-time streaming UI                       │
│  • Session management                           │
│  • Memory blocks editor                         │
│  • Rooms/Channels overview                      │
│  • Cost & token tracking                        │
└─────────────────┬───────────────────────────────┘
                  │
                  │ HTTP/SSE/WebSocket
                  │
┌─────────────────▼───────────────────────────────┐
│           Backend (Python)                       │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │     Consciousness Loop                 │    │
│  │  • Model routing (OpenRouter)          │    │
│  │  • Stream management                   │    │
│  │  • Tool execution                      │    │
│  │  • Memory integration                  │    │
│  └────────────────────────────────────────┘    │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │     Daemon Mode (24/7 Runtime)         │    │
│  │  • Timer-based heartbeat               │    │
│  │  • Task scheduler                      │    │
│  │  • In-memory agent caching             │    │
│  │  • Graceful shutdown                   │    │
│  └────────────────────────────────────────┘    │
│                                                  │
│  ┌─────────────┐  ┌─────────────┐             │
│  │  Memory     │  │   Tools     │             │
│  │  System     │  │  Registry   │             │
│  │  + MIRAS    │  │             │             │
│  │ • Core      │  │ • Web       │             │
│  │ • Archival  │  │ • Search    │             │
│  │ • Embedding │  │ • Discord   │             │
│  │ • Retention │  │ • ArXiv     │             │
│  │ • Hebbian   │  │ • Jina      │             │
│  └─────────────┘  └─────────────┘             │
│                                                  │
│  ┌─────────────┐  ┌─────────────┐             │
│  │  Channels   │  │   Tasks     │             │
│  │  (Rooms)    │  │  Scheduler  │             │
│  │ • heartbeat │  │ • daily     │             │
│  │ • task      │  │ • weekly    │             │
│  │ • reflection│  │ • monthly   │             │
│  │ • threads   │  │ • custom    │             │
│  └─────────────┘  └─────────────┘             │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │        Graph RAG System               │    │
│  │  • Knowledge graph retrieval          │    │
│  │  • Neo4j (optional) or local DB       │    │
│  │  • Relationship extraction            │    │
│  └────────────────────────────────────────┘    │
│                                                  │
│  ┌────────────────────────────────────────┐    │
│  │        MCP Integration                 │    │
│  │  • Code execution sandbox              │    │
│  │  • Browser automation (Playwright)     │    │
│  │  • Skills learning system              │    │
│  │  • Vision analysis (Gemini)            │    │
│  └────────────────────────────────────────┘    │
└──────────────────┬──────────────────────────────┘
                   │
      ┌────────────┼────────────┬────────────┐
      │            │            │            │
┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐ ┌────▼─────┐
│PostgreSQL │ │ChromaDB│ │MCP Servers│ │  Neo4j   │
│Persistence│ │Vectors │ │(External) │ │(Optional)│
└───────────┘ └────────┘ └──────────┘ └──────────┘
```

---

## 🔧 Tech Stack

### Backend
- **Python 3.11+** - Core runtime
- **Flask** - API server with SSE streaming
- **PostgreSQL** - Primary database (conversation history, memory)
- **ChromaDB** - Vector embeddings for semantic search
- **Neo4j** - Graph database for Graph RAG (optional, local DB fallback)
- **OpenRouter** - Multi-model LLM gateway
- **RestrictedPython** - Sandboxed code execution

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Vite** - Build tool & dev server

### MCP Integration
- **Playwright** - Browser automation (Chromium)
- **Gemini 2.0 Flash** - Vision analysis (free tier)
- **fastmcp** - MCP protocol implementation
- **MCP Servers** - Stdio-based external tools

---

## 🛠️ Built-in Tools

### Memory Management
- `core_memory_append` - Add to agent's core memory
- `core_memory_replace` - Modify core memory
- `archival_memory_insert` - Store in long-term memory
- `archival_memory_search` - Semantic search across memories

### Miras Memory Architecture
Advanced memory features based on Google Research:
- `retention_gate.compute_retention()` - Calculate memory retention score
- `attentional_bias.compute_attention_score()` - Multi-factor relevance scoring
- `hierarchical_memory.store()` - Store in tiered memory system
- `memory_learner.on_memories_accessed()` - Record Hebbian associations
- `memory_learner.record_feedback()` - Learn from user feedback

### Web & Research
- `fetch_webpage` - Retrieve and parse web pages
- `web_search` - DuckDuckGo search
- `arxiv_search` - Academic paper search
- `jina_reader` - Advanced web content extraction

### Integration
- `discord_send_message` - Discord bot integration
- `spotify_control` - Spotify playback control
- `execute_code` - Sandboxed Python execution (MCP)

### Graph RAG
- `/api/graph/nodes` - Get graph nodes
- `/api/graph/edges` - Get graph relationships
- `/api/graph/stats` - Graph statistics
- `/api/graph/rag` - Retrieve context from knowledge graph

### Rooms/Channels
- `/api/channels` - List/Create channels (rooms)
- `/api/channels/<id>/messages` - Get/Post channel messages
- `/api/messages/<id>/threads` - Discord-style thread system
- Default channels: `heartbeat-log`, `task`, `reflection`

### Task Scheduler
- `/api/tasks` - List/Create scheduled tasks
- `/api/tasks/<id>` - Get/Update/Delete task
- Schedules: `daily`, `weekly`, `monthly`, `custom` (every N days)

### Heartbeat System
- `/api/heartbeat/config` - Get/Update heartbeat configuration
- `/api/heartbeat/rules` - Manage heartbeat rules
- `/api/heartbeat/status` - Daemon & agent status
- `/api/heartbeat/trigger` - Manual heartbeat trigger (testing)
- `/api/heartbeat/templates` - Predefined rule templates

### Browser Automation (MCP)
- `navigate` - Browser navigation
- `screenshot` - Capture with vision analysis
- `extract_text` - DOM text extraction
- `click` / `fill_form` - Page interaction
- `search_google` - Google search automation

---

## 📦 Installation

### Prerequisites
- Python 3.11+ (3.11 or 3.12 recommended; 3.13 supported but may require additional setup)
- Node.js 18+
- PostgreSQL 14+ (optional, SQLite fallback available)
- OpenRouter API key

> **Note for Python 3.13 users**: Some packages may require newer versions. See [Python 3.13 Compatibility Guide](backend/PYTHON_3.13_COMPATIBILITY.md) for detailed instructions.

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# If using Python 3.13 on Windows and encountering wheel issues, see:
# backend/PYTHON_3.13_COMPATIBILITY.md

# Configure environment
cp config/.env.example .env
# Edit .env with your API keys

# Optional: Install Playwright for MCP browser automation
playwright install chromium
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

---

## 🔐 Security Features

### Code Execution Sandbox
- ✅ RestrictedPython compilation (no unsafe operations)
- ✅ 30-second timeout enforcement
- ✅ 512MB memory limit per execution
- ✅ Isolated workspace per session
- ✅ No file system access outside sandbox
- ✅ No network access except via MCP tools

### Browser Automation Security
- ✅ Domain whitelist (Wikipedia, GitHub, ArXiv, etc.)
- ✅ Domain blacklist (banking, payments blocked)
- ✅ Rate limiting (10 nav/min, 5 screenshots/min)
- ✅ Headless mode only (no GUI)
- ✅ HTTPS enforcement on sensitive operations

### API Security
- ✅ Rate limiting on all endpoints
- ✅ CORS configuration
- ✅ Input sanitization
- ✅ API key validation

📋 **Full audit:** See [FINAL_SECURITY_CHECK.md](FINAL_SECURITY_CHECK.md)

---

## 🚦 Usage Examples

### Basic Chat

```python
# The agent maintains context across messages
User: "My name is Alex"
Agent: "Nice to meet you, Alex! I've stored that in my memory."

User: "What's my name?"
Agent: "Your name is Alex!"
```

### Tool Usage

```python
# Memory tools
User: "Remember that I'm learning Python"
Agent: *uses core_memory_append*
Agent: "I've added that to my memory about you!"

# Web search
User: "What's the latest on quantum computing?"
Agent: *uses web_search*
Agent: "Here's what I found about quantum computing..."
```

### MCP Code Execution

```python
# Browser automation with vision
User: "Take a screenshot of Wikipedia's homepage and describe it"
Agent: *writes code*
```
```python
url = "https://en.wikipedia.org"
result = await mcp.browser.screenshot(url, analyze=True)
print(result['analysis'])
```

**Result:** Vision analysis returned, 98.7% token savings vs manual browsing

📖 **Full MCP guide:** See [MCP_SYSTEM_OVERVIEW.md](MCP_SYSTEM_OVERVIEW.md)

---

## 📊 Performance

### Token Efficiency
- **Without MCP:** ~100,000 tokens for complex web tasks
- **With MCP:** ~2,000 tokens (98.7% reduction)
- **Streaming:** <50ms first token latency

### Context Optimization (v1.2.1)
- **History Limit:** 12 messages (optimized from 20, ~40% fewer context tokens)
- **Auto-Summary:** Triggers automatically when >30 messages accumulate
- **Timeout:** 120s (allows large context window processing)
- **Max Response:** 8192 tokens (full detailed responses, not clipped)

### Execution Speed
- **Code compilation:** <50ms (RestrictedPython)
- **Typical execution:** 200-500ms
- **Max timeout:** 30s (enforced)

### Memory Performance
- **Core memory:** O(1) access (PostgreSQL indexed)
- **Archival search:** <200ms (ChromaDB vector similarity)
- **Skills lookup:** O(log n) with semantic indexing

---

## 🧪 Testing

```bash
# Backend tests
cd backend
python test_startup.py

# Integration tests
python test_mcp_integration.py

# Full test results
cat ../TESTING_RESULTS.md
```

---

## 🗺️ Roadmap

### Completed ✅
- [x] Multi-model OpenRouter integration
- [x] Streaming SSE responses
- [x] PostgreSQL persistence
- [x] Memory system (core + archival)
- [x] Tool execution framework
- [x] MCP code execution sandbox
- [x] Browser automation (Playwright)
- [x] Vision analysis (Gemini)
- [x] Skills learning system
- [x] Cost tracking
- [x] **Miras Memory Architecture** (December 2025)
  - [x] Retention Gates (dynamic memory decay/boost)
  - [x] Attentional Bias (multi-factor retrieval scoring)
  - [x] Hierarchical Memory (Working → Episodic → Semantic)
  - [x] Online Learning (Hebbian associations + feedback)
- [x] **Autonomous Agent System** (January 2026)
  - [x] Heartbeat System (timer-based with probability)
  - [x] Rooms/Channels (Discord-style organization)
  - [x] Task Scheduler (daily, weekly, monthly, custom)
  - [x] Daemon Mode (24/7 runtime with agent caching)
  - [x] DST-safe timezone handling
- [x] **Context & Token Optimization** (January 2026)
  - [x] Reduced history_limit (20 → 12) for ~40% token savings
  - [x] Auto-summary trigger at >30 messages
  - [x] Extended timeout (60s → 120s) for large contexts
  - [x] Flexible max_completion_tokens (8192 default)

### In Progress 🚧
- [ ] Additional MCP servers (filesystem, database)
- [ ] Collaborative skill libraries
- [ ] Advanced prompt engineering UI
- [ ] Multi-agent orchestration

### Planned 🎯
- [ ] Voice interface
- [ ] Mobile app
- [ ] Cloud deployment templates
- [ ] Plugin marketplace

---

## 🤝 Contributing

This is an open-source project. Contributions welcome!

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Standards
- Python: PEP 8, type hints, docstrings
- TypeScript: ESLint, Prettier, strict mode
- Tests: Add tests for new features
- Docs: Update relevant documentation

---

## 📄 License

See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

### Technologies
- **OpenRouter** - Multi-model API gateway
- **Anthropic MCP** - Model Context Protocol architecture
- **Playwright** - Browser automation framework
- **Gemini** - Vision analysis (Google)
- **PostgreSQL** - Database engine
- **ChromaDB** - Vector embeddings

### Research
- **Google Titans/Miras** - Advanced memory architecture (Retention Gates, Attentional Bias, Online Learning)
- **"It's All Connected"** - Test-time memorization and retention research

### Community
Built with inspiration from:
- Letta (formerly MemGPT) - Memory architecture patterns
- LangChain - Tool execution concepts
- AutoGPT - Agent autonomy ideas

---

## 📧 Support

- 🐛 **Bug Reports:** GitHub Issues
- 💬 **Questions:** GitHub Discussions
- 📖 **Documentation:** See `/docs` folder
- 🔧 **Troubleshooting:** See [QUICK_START.md](QUICK_START.md)

---

**Built for developers who need production-ready AI agents.**

*Version 1.2.1 | Last Updated: January 2026*

---

## 🧠 Miras Memory Architecture Details

Based on [Google Research Titans & Miras papers](https://research.google/blog/titans-miras-helping-ai-have-long-term-memory/), this framework implements a 4-phase advanced memory system:

### Phase 1: Retention Gates (~490 lines)
**File:** `backend/core/retention_gate.py`

Dynamic memory decay/boost based on:
- Importance (35% weight)
- Access count (30% weight)  
- Temporal recency (25% weight)
- Base retention (10% weight)

```python
from core.retention_gate import RetentionGate

gate = RetentionGate()
score = gate.compute_retention(memory)  # 0.0 - 1.0
action = gate.get_action(score)  # BOOST, KEEP, CONSOLIDATE, DECAY, ARCHIVE
```

### Phase 2: Attentional Bias (~610 lines)
**File:** `backend/core/attentional_bias.py`

5 attention modes with automatic query analysis:
- STANDARD - Balanced retrieval
- SEMANTIC_HEAVY - Meaning-focused
- TEMPORAL_HEAVY - Time-sensitive ("when did we...")
- IMPORTANCE_HEAVY - Critical information
- EMOTIONAL - Relationship/feeling queries

```python
from core.attentional_bias import QueryAnalyzer, AttentionalBias

analyzer = QueryAnalyzer()
mode = analyzer.analyze("When did we last meet?")  # → TEMPORAL

bias = AttentionalBias()
score = bias.compute_attention_score(memory, query, mode)
```

### Phase 3: Hierarchical Memory (~720 lines)
**File:** `backend/core/hierarchical_memory.py`

3-tier memory architecture:
- **Working Memory** - Fast, volatile, LRU eviction (current session)
- **Episodic Memory** - Medium-term, retention gates (recent history)
- **Semantic Memory** - Long-term, Graph DB integration (permanent knowledge)

```python
from core.hierarchical_memory import HierarchicalMemory, MemoryItem

hier = HierarchicalMemory()
hier.store(memory_item)  # Auto-routes to appropriate tier
hier.consolidate()  # Move memories between tiers
```

### Phase 4: Online Learning (~500 lines)
**File:** `backend/core/memory_learner.py`

Hebbian learning: "Neurons that fire together, wire together"
- Memories accessed together form associations
- User feedback adjusts importance
- Association decay for unused connections

```python
from core.memory_learner import MemoryLearner, FeedbackType

learner = MemoryLearner()
learner.on_memories_accessed(['mem1', 'mem2'], query="...")  # Forms associations
learner.record_feedback('mem1', FeedbackType.HELPFUL)  # +0.5 importance
learner.record_feedback('mem2', FeedbackType.NOT_HELPFUL)  # -0.2 importance
```

**Total: ~2,320 lines of research-backed memory architecture!**

📖 **Full documentation:** See [docs/MIRAS_TITANS_INTEGRATION.md](docs/MIRAS_TITANS_INTEGRATION.md)

---

## 💓 Heartbeat & Autonomous Agent System Details

Always-on agent capabilities for 24/7 autonomous operation.

### Daemon Mode
**File:** `backend/core/daemon_mode.py`

24/7 runtime with hot agent caching:
- Agents stay in memory (no restart overhead!)
- Connection pooling (PostgreSQL stays warm)
- Graceful shutdown (no data loss)
- Signal handling (SIGTERM, SIGINT)

```python
from core.daemon_mode import SubstrateAIDaemon, create_daemon_from_env

# Create and start daemon
daemon = create_daemon_from_env()
daemon.start()

# Load agent (stays in memory!)
agent = daemon.get_or_create_agent("my-agent", "My Agent Name")

# Check status
daemon.print_status()
```

### Heartbeat System
**File:** `backend/core/daemon_mode.py`

Timer-based agent activation with configurable rules:

```python
# Example heartbeat configuration (stored in agent.config)
heartbeat_config = {
    "enabled": True,
    "timezone": "Europe/Berlin",  # DST-safe!
    "rules": [
        {
            "id": "rule-uuid",
            "name": "Morning Check-in",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "start_time": "08:00",
            "end_time": "12:00",
            "interval_minutes": 60,
            "probability": 0.8  # 80% chance to trigger when timer fires
        },
        {
            "id": "rule-uuid-2",
            "name": "Evening Reflection",
            "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "start_time": "18:00",
            "end_time": "20:00",
            "interval_minutes": 45,
            "probability": 0.9
        }
    ]
}
```

**How it works:**
1. Timer fires at random interval (50-100% of configured interval)
2. Probability check determines if heartbeat triggers
3. Heartbeat message sent to agent via ConsciousnessLoop
4. Agent can respond, use tools, organize memories
5. Messages posted to `heartbeat-log` channel AND main thread

### Task Scheduler
**File:** `backend/core/task_scheduler.py`

Automatic task execution with multiple schedule types:

```python
from core.task_scheduler import TaskScheduler, calculate_next_run

# Schedule types
next_run = calculate_next_run('daily', '09:00')                    # Every day at 09:00
next_run = calculate_next_run('weekly', '10:00', days_of_week=[0, 2, 4])  # Mon/Wed/Fri
next_run = calculate_next_run('monthly', '12:00')                  # Monthly at 12:00
next_run = calculate_next_run('custom', '08:00', every_n_days=3)   # Every 3 days

# Task structure (stored in PostgreSQL)
task = {
    "task_name": "Daily Summary",
    "description": "Generate daily activity summary",
    "schedule": "daily",
    "time": "18:00",
    "action_type": "self_task",  # Send to agent
    "action_template": "Please summarize today's activities.",
    "one_time": False  # Recurring
}
```

**Features:**
- One-time and recurring tasks
- Automatic `next_run` calculation
- DST-safe timezone handling
- Integration with ConsciousnessLoop
- Channel-based message organization

### Rooms/Channels
**File:** `backend/api/routes_channels.py`

Discord-style message organization:

```
Agent
├── heartbeat-log   (System heartbeats)
├── task            (Scheduled tasks)
├── reflection      (Agent reflections)
└── [custom]        (User-created channels)
```

**Features:**
- Default channels auto-created per agent
- Messages posted to BOTH channel AND main thread
- Thread system for message replies
- Discord webhook integration (optional)

### API Endpoints

```bash
# Heartbeat Configuration
GET  /api/heartbeat/config?agent_id=default
PUT  /api/heartbeat/config
GET  /api/heartbeat/rules?agent_id=default
POST /api/heartbeat/rules
PUT  /api/heartbeat/rules/<rule_id>
DELETE /api/heartbeat/rules/<rule_id>
GET  /api/heartbeat/status
POST /api/heartbeat/trigger
GET  /api/heartbeat/templates

# Tasks
GET  /api/tasks?agent_id=default
POST /api/tasks
GET  /api/tasks/<task_id>
PUT  /api/tasks/<task_id>
DELETE /api/tasks/<task_id>

# Channels
GET  /api/channels?agent_id=default
POST /api/channels
GET  /api/channels/<channel_id>/messages
POST /api/channels/<channel_id>/messages
```

📖 **Implementation details:** See [IMPLEMENTATION_PLAN_HEARTBEAT_ROOMS.md](IMPLEMENTATION_PLAN_HEARTBEAT_ROOMS.md)


