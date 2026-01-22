# PostgreSQL Setup (Optional)

Substrate AI works perfectly with **SQLite only** (default). PostgreSQL is **optional** and provides advanced features for production deployments.

## When to Use PostgreSQL?

**SQLite is fine for:**
- Personal use
- Testing
- Single-user deployments
- Getting started

**Use PostgreSQL for:**
- Multi-agent deployments
- Production environments
- Advanced persistence features
- Message continuity across restarts
- Semantic search with pgvector

## Setup PostgreSQL (Optional)

### 1. Install PostgreSQL

**macOS:**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Linux:**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download from https://www.postgresql.org/download/windows/

### 2. Create Database

```bash
# Connect to PostgreSQL
psql postgres

# Create database and user
CREATE DATABASE substrate_ai;
CREATE USER substrate_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE substrate_ai TO substrate_user;

# Exit
\q
```

### 3. Configure Environment

Edit `.env`:

```bash
# Enable PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=substrate_ai
POSTGRES_USER=substrate_user
POSTGRES_PASSWORD=your_secure_password
```

### 4. Install pgvector (Optional - for semantic search)

```bash
# macOS
brew install pgvector

# Linux
sudo apt-get install postgresql-16-pgvector

# Or compile from source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

Enable in database:
```sql
psql substrate_ai
CREATE EXTENSION vector;
```

### 5. Start Backend

The backend will automatically:
- Detect PostgreSQL configuration
- Create required tables
- Enable advanced features
- Fall back to SQLite if PostgreSQL is unavailable

```bash
python api/server.py
```

You'll see:
```
🐘 PostgreSQL ACTIVATED!
✅ Message Continuity + Memory Coherence ONLINE!
```

## Features with PostgreSQL

### Message Continuity
- Conversations persist across restarts
- No data loss on server crash
- Automatic recovery

### Memory Coherence
- Advanced memory management
- Semantic search across memories
- Automatic summarization

### Multi-Agent Support
- Multiple agents share database
- Coordinated memory access
- Conflict resolution

## Disable PostgreSQL

Just remove PostgreSQL config from `.env`:

```bash
# Comment out or remove these lines:
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# ...
```

System will automatically fall back to SQLite.

## Troubleshooting

### "Could not connect to PostgreSQL"
- Check PostgreSQL is running: `pg_isready`
- Verify credentials in `.env`
- Check firewall allows port 5432

### "pgvector extension not found"
- pgvector is optional
- System works without it
- Install if you want semantic search

### "Permission denied"
```sql
-- Grant permissions
GRANT ALL ON SCHEMA public TO substrate_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO substrate_user;
```

## Security Notes

- **Never commit `.env` to git**
- Use strong PostgreSQL passwords
- Restrict PostgreSQL to localhost in production
- Enable SSL for remote connections
- Regular backups with `pg_dump`

## Migration from SQLite

If you start with SQLite and want to migrate to PostgreSQL later:

1. Export data from SQLite
2. Setup PostgreSQL
3. Import data
4. Update `.env`
5. Restart backend

(Detailed migration scripts coming soon)

---

**Remember:** PostgreSQL is **optional**. SQLite works great for most use cases!

