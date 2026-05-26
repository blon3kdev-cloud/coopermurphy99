# Deploy tutorial — single VPS

This guide deploys the full **kwk** stack on one Linux VPS:

| Component | Role |
|-----------|------|
| **nginx** | HTTPS, static React build, reverse proxy `/api` → backend |
| **Backend** (FastAPI + uvicorn) | API on `127.0.0.1:4000`, Discord/Telegram bots |
| **MongoDB** | Hosted elsewhere (Atlas, etc.) — VPS only connects over the network |
| **Frontend** | Pre-built static files served by nginx |

Replace `yourdomain.com` with your real domain everywhere below.

---

## 0. What you need before starting

- A VPS (Ubuntu 22.04 or 24.04 recommended, 1–2 GB RAM is enough — no database on this machine)
- A domain with an **A record** pointing to the VPS public IP
- SSH access as a user with `sudo`
- Git repo URL (GitHub or self-hosted)
- **Remote MongoDB** connection string (e.g. MongoDB Atlas) and network access from the VPS IP
- Secrets ready: `DATABASE_URL`, `INTERNAL_SECRET`, admin credentials, optional bot tokens, payment keys

---

## 1. Initial server setup

SSH into the VPS:

```bash
ssh root@YOUR_VPS_IP
```

Create a deploy user (optional but recommended):

```bash
adduser deploy
usermod -aG sudo deploy
su - deploy
```

Update packages and install dependencies:

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y \
  git curl build-essential \
  nginx certbot python3-certbot-nginx \
  python3 python3-venv python3-pip \
  tesseract-ocr tesseract-ocr-pol
```

Install **Node.js 20 LTS** (required for npm scripts):

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v   # should be v20.x
npm -v
```

Open firewall (if `ufw` is enabled):

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

---

## 2. Remote MongoDB (not on the VPS)

MongoDB runs on a **separate host** (MongoDB Atlas, another VPS, managed cloud DB, etc.). The app only needs a reachable connection string in `backend/.env`.

### 2.1 Atlas (typical)

1. Create a cluster in [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. **Database Access** — create a DB user with read/write on your app database.
3. **Network Access** — allow the VPS:
   - **Access List**: add your VPS public IP (`curl -4 ifconfig.me` from the VPS), or
   - `0.0.0.0/0` only if you accept the security tradeoff (not recommended long term).
4. **Connect** → Drivers → copy the connection string.

Use the SRV form in `DATABASE_URL`:

```text
DATABASE_URL=mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

Database name: with `NODE_ENV=production`, the app uses database **`prod`** unless you set `MONGODB_DB` or put the name in the URL path, e.g.:

```text
DATABASE_URL=mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/prod?retryWrites=true&w=majority
```

Optional override:

```text
MONGODB_DB=prod
```

### 2.2 Self-hosted MongoDB on another server

Use a standard URI pointing at that host (not `127.0.0.1` on the app VPS):

```text
DATABASE_URL=mongodb://USER:PASSWORD@db.example.com:27017/prod?authSource=admin
```

Ensure firewall/security groups allow **outbound** from the VPS to the DB host on port `27017` (or `27017`–`27019` for replica sets).

### 2.3 Verify connectivity from the VPS

After `backend/.env` exists (step 4), test from the server:

```bash
cd /var/www/kwk/backend
.venv/bin/python -c "
from dotenv import load_dotenv; load_dotenv('.env')
import os, asyncio
from motor.motor_asyncio import AsyncIOMotorClient
async def main():
    c = AsyncIOMotorClient(os.environ['DATABASE_URL'])
    await c.admin.command('ping')
    print('MongoDB ping OK')
asyncio.run(main())
"
```

If this fails, fix Atlas IP allowlist, credentials, or TLS before starting the API.

---

## 3. Clone the project

```bash
sudo mkdir -p /var/www
sudo chown $USER:$USER /var/www
cd /var/www

git clone https://github.com/YOUR_ORG/kwk.git
cd kwk
```

Use your real remote URL. All paths below assume `/var/www/kwk`.

---

## 4. Configure environment files

### 4.1 Backend — `backend/.env`

```bash
cd /var/www/kwk/backend
cp .env.example .env
nano .env
```

**Production minimum** (edit values):

```env
NODE_ENV=production
PORT=4000
FRONTEND_ORIGIN=https://yourdomain.com
TRUSTED_PROXY=true

DATABASE_URL=mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/prod?retryWrites=true&w=majority

# Generate: openssl rand -hex 32
INTERNAL_SECRET=your-long-random-secret-here

# Non-default login name (not jrm8)
ADMIN_LOGIN=your_admin_name

# Argon2 hashes — see step 4.3
ADMIN_PIN_HASH=...
ADMIN_PASSWORD_HASH=...

# Remove or leave empty in production:
# DEV_LOGIN_CODE=
# ADMIN_PIN=
# ADMIN_PASSWORD=

BLIK_VERIFY_STRICT=true
BACKEND_URL=http://127.0.0.1:4000

# Bots (optional but typical for auth/rewards)
TELEGRAM_TOKEN=
DISCORD_TOKEN=
DISCORD_APP_ID=
# ... other DISCORD_* channel IDs from .env.example

# Crypto / iSports / Chainlink — fill if you use those features
```

Production **rejects** default admin plaintext and placeholder `INTERNAL_SECRET`. The deploy script runs `scripts/check_env.py` to validate this.

### 4.2 Hash admin credentials

On the server (after venv exists — step 5 creates it, or run once after first deploy attempt):

```bash
cd /var/www/kwk/backend
python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python scripts/hash_admin_credentials.py
```

Copy the printed `ADMIN_PIN_HASH` and `ADMIN_PASSWORD_HASH` into `backend/.env`. Remove `ADMIN_PIN` and `ADMIN_PASSWORD` in production.

### 4.3 Frontend — `frontend/.env`

For **same-origin** setup (nginx serves the SPA and proxies `/api`), leave the API URL empty:

```bash
cd /var/www/kwk/frontend
cp .env.example .env
nano .env
```

```env
# Empty = browser calls https://yourdomain.com/api/...
REACT_APP_API_URL=
```

Only set `REACT_APP_API_URL=https://api.otherhost.com` if the API is on a different host (then update nginx CSP — see `deploy/nginx/security-headers.conf`).

---

## 5. Install dependencies and build frontend

From repo root:

```bash
cd /var/www/kwk

# Backend
cd backend
npm install
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/check_env.py

# Frontend production build
cd ../frontend
npm install
export NODE_ENV=production
npm run build
```

Build output: `frontend/build/` (nginx will serve this).

Verify env again anytime:

```bash
cd /var/www/kwk/backend && .venv/bin/python scripts/check_env.py
```

---

## 6. systemd service for the backend

The backend runs API + bots via `backend/scripts/start.sh` (not nodemon in production).

Create `/etc/systemd/system/kwk-backend.service`:

```ini
[Unit]
Description=kwk backend (FastAPI + bots)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=/var/www/kwk/backend
Environment=NODE_ENV=production
EnvironmentFile=/var/www/kwk/backend/.env
ExecStart=/var/www/kwk/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 4000
# Bots are started by start.sh in dev; in production use a wrapper or separate units.
# Simple approach: use the project start script:
# ExecStart=/bin/sh /var/www/kwk/backend/scripts/start.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Recommended:** use the full start script so Discord/Telegram bots run with the API:

```ini
ExecStart=/bin/sh /var/www/kwk/backend/scripts/start.sh
```

Note: `start.sh` binds uvicorn to `0.0.0.0`. For nginx-only access, change the last line in `start.sh` to `--host 127.0.0.1` or keep firewall blocking port 4000 from the internet.

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kwk-backend
sudo systemctl start kwk-backend
sudo systemctl status kwk-backend
```

Logs:

```bash
journalctl -u kwk-backend -f
```

Health check (from the VPS):

```bash
curl -s http://127.0.0.1:4000/api/health
```

---

## 7. nginx — one host for site + API

Create `/etc/nginx/sites-available/kwk`:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

# Optional: WebSocket upgrade map (not required for Crash — it uses HTTP polling)
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # certbot will fill these after step 8:
    # ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    root /var/www/kwk/frontend/build;
    index index.html;

    # Security headers from the repo
    include /var/www/kwk/deploy/nginx/security-headers.conf;

    # React SPA
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API + SSE (bitcoin stream needs no buffering)
    location /api/ {
        limit_req zone=api burst=40 nodelay;

        proxy_pass http://127.0.0.1:4000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }

    # Optional: lock admin UI to office IPs (see deploy/nginx/admin-allowlist.conf.example)
    # location /admin { ... }
}
```

Enable the site:

```bash
sudo ln -sf /etc/nginx/sites-available/kwk /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 8. HTTPS with Let's Encrypt

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot updates the nginx SSL lines. Renewal is automatic via systemd timer.

---

## 9. Smoke test

From your laptop:

1. Open `https://yourdomain.com` — the app loads.
2. Open browser devtools → Network — API calls go to `https://yourdomain.com/api/...` (same origin).
3. `https://yourdomain.com/api/health` returns OK.
4. Admin login works with hashed credentials (not dev defaults).
5. If bots are configured, check Discord/Telegram respond; watch `journalctl -u kwk-backend -f`.

---

## 10. Deploy and update workflow

### First-time production deploy (manual)

Already done in steps 5–7. You can also use project scripts with `NODE_ENV=production` (foreground, good for debugging):

```bash
cd /var/www/kwk
export NODE_ENV=production
npm run deploy:backend   # blocks — use systemd instead on a server
npm run deploy:frontend  # builds + runs `serve` on port 3000 — prefer nginx for production
```

On a VPS, **prefer**: systemd for backend + nginx for static build (this guide).

### Pull updates from GitHub

The repo includes `npm run update` (pull, refresh deps, redeploy):

```bash
cd /var/www/kwk
git pull   # or: npm run update  (needs origin remote configured)
```

After pull, on production:

```bash
cd /var/www/kwk/backend
npm install
.venv/bin/pip install -r requirements.txt
sudo systemctl restart kwk-backend

cd /var/www/kwk/frontend
npm install
export NODE_ENV=production
npm run build
sudo systemctl reload nginx
```

Or from root (if you run deploy interactively during maintenance):

```bash
export NODE_ENV=production
cd /var/www/kwk
npm run update
```

Then restart systemd/nginx as above — do not leave `npm run deploy` running in production without a process manager.

---

## 11. Optional hardening

| Topic | Action |
|--------|--------|
| Rate limits | Already in nginx example; tune `deploy/nginx/api-rate-limit.conf.example` |
| Admin UI IP lock | `deploy/nginx/admin-allowlist.conf.example` |
| BLIK OCR | `tesseract-ocr` + `tesseract-ocr-pol` (step 1) |
| Backups | Use Atlas backups/snapshots, or `mongodump` from a trusted machine with your remote `DATABASE_URL` |
| Secrets | Never commit `.env`; restrict `chmod 600 backend/.env` |
| Port 4000 | Do not expose publicly; only nginx talks to `127.0.0.1:4000` |

---

## 12. Troubleshooting

| Symptom | Check |
|---------|--------|
| `check_env.py` fails | `INTERNAL_SECRET`, `ADMIN_*_HASH`, `DATABASE_URL`, production rules in `backend/app/safe_url.py` |
| API starts then DB errors | VPS IP on Atlas allowlist; correct `DATABASE_URL`; run ping test (step 2.3) |
| 502 on `/api` | `systemctl status kwk-backend`, `curl http://127.0.0.1:4000/api/health` |
| CORS errors | `FRONTEND_ORIGIN` must match `https://yourdomain.com` (with or without `www` — config adds both variants) |
| Wrong client IP in rate limits | `TRUSTED_PROXY=true` behind nginx |
| SPA routes 404 | `try_files ... /index.html` in nginx `location /` |
| SSE / live chart stuck | nginx `proxy_buffering off` on `/api/` (see step 7) |
| Crash multiplier frozen | `curl http://127.0.0.1:4000/api/games/crash/state` should return JSON; restart `kwk-backend` |
| Bots not running | Tokens in `.env`; use `ExecStart=.../scripts/start.sh` in systemd |
| Payments | `PAYMENT_WALLET_MNEMONIC` and related vars; production validates mnemonic length |

---

## 13. Quick reference — ports and paths

| Path / port | Purpose |
|-------------|---------|
| `/var/www/kwk` | Project root |
| `backend/.env` | API, DB, bots, payments |
| `frontend/.env` | Build-time `REACT_APP_*` |
| `frontend/build/` | Static files for nginx |
| `127.0.0.1:4000` | Backend (internal only) |
| `443` | Public HTTPS (nginx) |
| `npm run deploy` | Dev: both stacks in foreground |
| `npm run update` | Git pull + deps + redeploy scripts |

---

## 14. Minimal checklist

- [ ] DNS A record → VPS IP  
- [ ] Node 20, Python 3, tesseract, nginx, certbot installed  
- [ ] Remote MongoDB reachable from VPS (`DATABASE_URL`, Atlas IP allowlist)  
- [ ] `backend/.env` — `NODE_ENV=production`, secrets, Argon2 admin hashes  
- [ ] `frontend/.env` — `REACT_APP_API_URL=` empty for same-origin  
- [ ] `check_env.py` passes  
- [ ] `npm run build` in `frontend/`  
- [ ] `kwk-backend.service` enabled  
- [ ] nginx site enabled, SSL active  
- [ ] Health + login tested in browser  

You now have the app on a single VPS: **nginx → static React + `/api` proxy → FastAPI (+ bots) → remote MongoDB**.
