# PostgreSQL Deployment Guide for Koyeb

## Why SQLite Doesn't Work on Koyeb

**Koyeb is a serverless platform that:**
1. **Does NOT provide persistent filesystem** - Files written to disk are ephemeral
2. **Container instances can be replaced/recycled** at any time
3. **SQLite requires a persistent file** (`quizbot.db`) that would be lost on restart

**Consequences of using SQLite on Koyeb:**
- Database file gets deleted when container restarts
- All user data, quiz progress, and payments are lost
- Complete data loss on every deployment

**Solution:** Use an **external PostgreSQL database** (Supabase, Neon, Railway, etc.)

---

## Database Connection Code

### Using SQLAlchemy (Async) - Recommended

```python
# app/db/base.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

Base = declarative_base()

class Database:
    def __init__(self):
        engine_kwargs = {
            "echo": False,
            "pool_pre_ping": True,
            "future": True,
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "ssl": "require"  # Required for external PostgreSQL
        }

        self.engine = create_async_engine(
            settings.DATABASE_URL,
            **engine_kwargs
        )
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            future=True
        )

db = Database()
```

### Using psycopg2 (Sync Alternative)

```python
import psycopg2
from psycopg2 import pool

# Connection pool
pg_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    sslmode="require"  # Required for production
)

# Get connection
conn = pg_pool.getconn()
```

---

## Environment Variables for Koyeb

### Option 1: Using DATABASE_URL (Recommended)

Set this single environment variable in Koyeb:

```
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname?sslmode=require
```

**Example for Supabase:**
```
DATABASE_URL=postgresql+asyncpg://postgres:abc123@db.xyz.supabase.co:5432/postgres?sslmode=require
```

**Example for Neon:**
```
DATABASE_URL=postgresql+asyncpg://user:password@ep-xyz.us-east-1.aws.neon.tech/quizbot?sslmode=require
```

**Example for Railway:**
```
DATABASE_URL=postgresql+asyncpg://user:password@containers-us-west-1.railway.app:5432/railway?sslmode=require
```

### Option 2: Using Individual Variables

```
DB_TYPE=postgresql
DB_HOST=db.xyz.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_password
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

---

## requirements.txt

```txt
# Database - PostgreSQL (required for Koyeb)
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
psycopg2-binary>=2.9.0

# Removed SQLite (not supported on Koyeb)
# aiosqlite>=0.19.0
```

---

## How to Set Up PostgreSQL

### Option 1: Supabase (Free Tier Available)

1. Go to https://supabase.com
2. Create new project
3. Go to Settings > Database
4. Copy connection string
5. **Important:** Change `postgres://` to `postgresql+asyncpg://`

### Option 2: Neon (Free Tier Available)

1. Go to https://neon.tech
2. Create new project
3. Go to Connection Details
4. Copy connection string
5. Add `?sslmode=require` at the end

### Option 3: Railway (Pay as you go)

1. Go to https://railway.app
2. Create new PostgreSQL service
3. Go to Connect tab
4. Copy connection string

### Option 4: Koyeb Database (Integration)

Koyeb now offers managed PostgreSQL:
1. Go to Koyeb dashboard
2. Create new service
3. Select "Add Database"
4. Choose PostgreSQL
5. Connection details will be auto-injected as `DATABASE_URL`

---

## Migration from SQLite to PostgreSQL

### Step 1: Export SQLite Data

```python
# scripts/migrate_to_postgres.py
import sqlite3
import json

conn = sqlite3.connect('data/quizbot.db')
cursor = conn.cursor()

# Export all tables
tables = ['users', 'questions', 'subjects', 'chapters', 
          'user_progress', 'quiz_attempts', 'payments', 
          'leaderboard', 'user_daily_limits', 'admin_users']

exported_data = {}
for table in tables:
    cursor.execute(f"SELECT * FROM {table}")
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    exported_data[table] = {
        'columns': columns,
        'rows': rows
    }

with open('migration_data.json', 'w') as f:
    json.dump(exported_data, f, default=str)

conn.close()
```

### Step 2: Import to PostgreSQL

```python
# scripts/import_from_json.py
import json
import psycopg2

with open('migration_data.json') as f:
    data = json.load(f)

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

for table, content in data.items():
    columns = content['columns']
    rows = content['rows']
    
    for row in rows:
        placeholders = ','.join(['%s'] * len(row))
        query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
        cursor.execute(query, row)
    
    conn.commit()

cursor.close()
conn.close()
```

---

## Production-Ready Configuration

### app/config.py

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    DATABASE_URL: str = Field(default="", description="Full PostgreSQL connection URL")
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)
    
    @property
    def DATABASE_URL(self) -> str:
        env_db = os.getenv("DATABASE_URL")
        if env_db:
            return env_db
        # Fallback construction if using individual vars
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
```

### app/db/base.py

```python
class Database:
    def __init__(self):
        engine_kwargs = {
            "echo": False,
            "pool_pre_ping": True,
            "future": True,
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "ssl": "require",  # Critical for production
            "connect_timeout": 30,
            "command_timeout": 30,
        }

        self.engine = create_async_engine(
            settings.DATABASE_URL,
            **engine_kwargs
        )
```

---

## Koyeb Deployment Checklist

- [ ] Create PostgreSQL database (Supabase/Neon/Railway/Koyeb)
- [ ] Get connection string
- [ ] Convert connection string to `postgresql+asyncpg://` format
- [ ] Set `DATABASE_URL` in Koyeb environment variables
- [ ] Update `requirements.txt` (remove aiosqlite, add psycopg2-binary)
- [ ] Test connection locally first
- [ ] Migrate existing data (if any)
- [ ] Deploy to Koyeb
- [ ] Verify database connectivity in logs
- [ ] Test a write operation (e.g., new user registration)

---

## Troubleshooting

### Connection Refused
```
could not connect to server: Connection refused
```
- Check if database host/port is correct
- Ensure firewall allows connections
- For Supabase/Neon: Check IP allowlist

### SSL Connection Required
```
sslmode value "require" invalid
```
- Remove `?sslmode=require` from connection string
- Add `ssl="require"` in engine kwargs instead

### Password Contains Special Characters
```
invalid password
```
- URL-encode the password:
```python
import urllib.parse
encoded_password = urllib.parse.quote(password, safe='')
```

### Connection Timeout
```
could not connect to server: Operation timed out
- Increase `connect_timeout` in engine kwargs
- Check if database is in the same region as Koyeb service

