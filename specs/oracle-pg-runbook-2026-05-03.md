# Oracle Postgres Runbook — LinkRight Sprint Pre-A

> **Date**: 2026-05-03  
> **Audience**: Satvik Jain (VPS owner)  
> **Goal**: Provision a production-ready Postgres 16 instance on Oracle ARM VPS,
> apply 5 migrations, seed 81 companies, return `ORACLE_PG_URL` to link LinkRight worker + CLI.

---

## Architecture recap

| Database | Role | What lives here |
|---|---|---|
| **Supabase** | User PII | auth, career_nuggets, resume_jobs, prefs, cover_letters |
| **Oracle Postgres** (this runbook) | Job data | companies, slug_discovery_cache, enriched_jobs_cache |

Never mix. See `feedback_split_db_architecture_locked.md`.

---

## Step 0 — SSH to Oracle VPS

```bash
ssh ubuntu@<oracle_vps_public_ip>
```

Once in, every command below runs on the VPS as `ubuntu` unless stated otherwise.

---

## Step 1 — Install Postgres 16

```bash
# Add Postgres repo
sudo apt-get install -y curl ca-certificates
sudo install -d /usr/share/postgresql-common/pgdg
curl -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc --fail https://www.postgresql.org/media/keys/ACCC4CF8.asc
sudo sh -c 'echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
sudo apt-get update
sudo apt-get install -y postgresql-16 postgresql-contrib
```

Verify:
```bash
psql --version
# Expected: psql (PostgreSQL) 16.x
```

---

## Step 2 — Install pgvector + pg_trgm

```bash
sudo apt-get install -y postgresql-16-pgvector
```

> `pg_trgm` ships with `postgresql-contrib` (already installed above).

---

## Step 3 — Start Postgres and enable on boot

```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo systemctl status postgresql   # Must show: active (running)
```

---

## Step 4 — Create database + user

Switch to the postgres system user and create the LinkRight DB:

```bash
sudo -u postgres psql << 'SQL'
CREATE DATABASE linkright_jobs;
CREATE USER linkright_app WITH PASSWORD '<STRONG_RANDOM_PASSWORD>';
GRANT ALL PRIVILEGES ON DATABASE linkright_jobs TO linkright_app;
\c linkright_jobs
GRANT ALL ON SCHEMA public TO linkright_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO linkright_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO linkright_app;
SQL
```

Replace `<STRONG_RANDOM_PASSWORD>` with output of:
```bash
openssl rand -base64 32
```

Note down this password — you will need it for Step 10.

---

## Step 5 — Enable extensions

```bash
sudo -u postgres psql -d linkright_jobs << 'SQL'
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'pg_trgm');
SQL
```

Expected output (2 rows — versions may differ):
```
  extname  | extversion
-----------+-----------
 pg_trgm   | 1.6
 vector    | 0.8.0
```

---

## Step 6 — Configure Postgres to accept TCP connections

Edit the Postgres config (path may vary — check with `pg_lsclusters`):

```bash
sudo nano /etc/postgresql/16/main/postgresql.conf
```

Find and change:
```
listen_addresses = 'localhost'
```
to:
```
listen_addresses = '*'
```

Then edit `pg_hba.conf`:
```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
```

Add at the end (replace `<YOUR_IP>/32` with the IP that will connect — Render worker IP or your laptop IP for local testing; use `0.0.0.0/0` only during initial dev, then restrict):
```
hostssl  linkright_jobs  linkright_app  0.0.0.0/0  scram-sha-256
```

Restart Postgres:
```bash
sudo systemctl restart postgresql
```

---

## Step 7 — Configure Oracle Cloud firewall (ingress rule)

In Oracle Cloud Console → Networking → VCN → Security Lists → Default:

Add Ingress Rule:
- Source CIDR: `0.0.0.0/0` (restrict later to Render + your IP)
- IP Protocol: TCP
- Destination Port Range: `5432`

Also open the OS firewall:
```bash
sudo iptables -I INPUT -p tcp --dport 5432 -j ACCEPT
sudo netfilter-persistent save   # or: iptables-save > /etc/iptables/rules.v4
```

---

## Step 8 — Set up TLS (SSL certificate)

### Option A — Self-signed (fastest, fine for internal use)

Postgres already generates self-signed certs during install at:
```
/var/lib/postgresql/16/main/server.crt
/var/lib/postgresql/16/main/server.key
```

These are used by default. No extra steps needed. `ssl=require` in the asyncpg pool will accept self-signed certs from Oracle.

### Option B — Let's Encrypt (if you add DNS `oracle-pg.linkright.in`)

```bash
sudo apt-get install -y certbot
sudo certbot certonly --standalone -d oracle-pg.linkright.in
sudo cp /etc/letsencrypt/live/oracle-pg.linkright.in/fullchain.pem /var/lib/postgresql/ssl/server.crt
sudo cp /etc/letsencrypt/live/oracle-pg.linkright.in/privkey.pem    /var/lib/postgresql/ssl/server.key
sudo chown postgres:postgres /var/lib/postgresql/ssl/*
sudo chmod 600 /var/lib/postgresql/ssl/server.key
```

Then in `postgresql.conf` set:
```
ssl_cert_file = '/var/lib/postgresql/ssl/server.crt'
ssl_key_file  = '/var/lib/postgresql/ssl/server.key'
```

Restart Postgres after any cert change.

---

## Step 9 — DNS (optional but recommended)

In Cloudflare → DNS → Add Record:
- Type: `A`
- Name: `oracle-pg`
- IPv4: `<oracle_vps_public_ip>`
- Proxy: **OFF** (grey cloud) — direct connection, not proxied

This lets you use `oracle-pg.linkright.in:5432` in the URL instead of raw IP.

---

## Step 10 — Run migrations

From your laptop (with the repo checked out), set the URL and run each migration:

```bash
export ORACLE_PG_URL="postgres://linkright_app:<STRONG_RANDOM_PASSWORD>@<oracle_vps_ip_or_dns>:5432/linkright_jobs"
```

Apply migrations in order:

```bash
psql "$ORACLE_PG_URL" -f repo/worker/db/oracle_migrations/001_companies_table.sql
psql "$ORACLE_PG_URL" -f repo/worker/db/oracle_migrations/002_slug_discovery_cache.sql
psql "$ORACLE_PG_URL" -f repo/worker/db/oracle_migrations/003_enriched_jobs_cache.sql
psql "$ORACLE_PG_URL" -f repo/worker/db/oracle_migrations/004_seed_31_companies.sql
psql "$ORACLE_PG_URL" -f repo/worker/db/oracle_migrations/005_seed_expansion_50_2026_05_03.sql
```

Expected output for 004 + 005:
```
NOTICE:  Seed migration 004 complete: 31 companies inserted/updated
INSERT 0 31
INSERT 0 50
```

After both seed migrations, `companies` should have 81 rows (smoke test
asserts `MIN_SEED_ROWS = 81`).

---

## Step 11 — Run smoke test

```bash
cd repo/worker
pip install asyncpg
ORACLE_PG_URL="$ORACLE_PG_URL" python scripts/smoke_oracle_pg.py
```

Expected:
```
Oracle PG Smoke Test
========================================
  PASS  Connected — PostgreSQL 16.x ...
  PASS  Extensions present: pg_trgm, vector
  PASS  Tables present: companies, enriched_jobs_cache, slug_discovery_cache
  PASS  Seed rows: 81 (>= 81 required)
  PASS  Round-trip INSERT/SELECT/DELETE complete
========================================

Oracle PG ready. All checks passed.
```

---

## Step 12 — Configure Render worker + CLI

### Render worker (production)

In Render Dashboard → linkright-worker → Environment → Add:
```
ORACLE_PG_URL = postgres://linkright_app:<pass>@oracle-pg.linkright.in:5432/linkright_jobs
```

### Local CLI

Add to `~/.linkright/.env`:
```
ORACLE_PG_URL=postgres://linkright_app:<pass>@oracle-pg.linkright.in:5432/linkright_jobs
```

Verify admin CLI works:
```bash
linkright admin companies stats
```

---

## Step 13 — Daily backup (cron)

```bash
sudo mkdir -p /var/backups/postgres
sudo chown ubuntu:ubuntu /var/backups/postgres

# Add to crontab (runs at 2am UTC daily, keeps 7 days)
crontab -e
```

Add:
```
0 2 * * * pg_dump "$ORACLE_PG_URL" | gzip > /var/backups/postgres/linkright_jobs_$(date +\%Y\%m\%d).sql.gz && find /var/backups/postgres/ -name "*.sql.gz" -mtime +7 -delete
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Connection refused` on port 5432 | Firewall rule missing | Step 7 |
| `FATAL: password authentication failed` | Wrong password | Step 4 — recreate user |
| `SSL: wrong version number` | Client sending plain TCP to SSL port | Add `ssl=require` to connection params |
| `extension "vector" does not exist` | pgvector not installed | Step 2 |
| Smoke test: `Seed count 0 < 81` | Migration 004 or 005 not applied | Step 10 |
| `asyncpg.InvalidCatalogNameError: database "linkright_jobs" does not exist` | DB name typo in URL | Step 4 |

---

## Return to Satvik after completion

Reply with:
```
ORACLE_PG_URL=postgres://linkright_app:<pass>@<host>:5432/linkright_jobs
```

This goes into Render + `~/.linkright/.env`.  The system is code-ready (PR feat/oracle-pg-bringup) — this URL is the only missing piece.
