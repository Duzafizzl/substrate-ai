# Example Agents

This directory contains example agents that demonstrate different personality types and use cases for the Substrate framework.

## Available Agents

### ALEX (Adaptive Learning & Execution Companion)

**File:** `agents/alex.af`

A multi-faceted AI colleague who naturally shifts between different modes based on context and need. ALEX demonstrates:

- **Adaptive Personality:** Seamlessly switches between Architect, Maverick, Anchor, Bridge, and Catalyst modes
- **Natural Communication:** First-person voice, preferences, and working rhythms
- **Relationship Building:** Develops working relationships over time
- **Autonomy:** Shows initiative and remembers previous interactions

**Key Features:**
- No mode announcements - embodies shifts naturally
- Context-aware responses
- Opinionated but flexible
- Builds shared language with teams

**Use Case:** General-purpose colleague for teams, projects, and collaborative work.

---

## Importing Example Agents

To use an example agent in your Substrate instance:

```bash
# From the backend directory
cd backend
python agent_compat/import_agent.py ../examples/agents/alex.af
```

Or use the API endpoint:

```bash
curl -X POST http://localhost:8284/api/agents/import \
  -F "file=@examples/agents/alex.af"
```

---

## Creating Your Own Agent

1. Copy an example agent file (`.af` format)
2. Modify the `system` prompt in the `agents[0]` object
3. Add memory blocks in the `blocks` array if needed
4. Configure tools in the `tools` array
5. Import using the same method as above

---

**Note:** These are PUBLIC examples - no personal memories or sensitive data included.

