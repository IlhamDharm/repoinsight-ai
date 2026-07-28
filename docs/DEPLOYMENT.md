# RepoInsight AI — Deployment Guide

## Overview

RepoInsight AI is an AI-powered GitHub repository analysis platform built with FastAPI (Python) and React (TypeScript). This guide covers deployment across multiple targets: Docker (template), VPS, Railway, and Render.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Docker Deployment](#docker-deployment)
3. [VPS Deployment](#vps-deployment)
4. [Railway Deployment](#railway-deployment)
5. [Render Deployment](#render-deployment)
6. [Nginx Configuration](#nginx-configuration)
7. [SSL/TLS](#ssltls)
8. [Production Environment Variables](#production-environment-variables)
9. [Database Backup](#database-backup)
10. [Monitoring](#monitoring)

---

## Prerequisites

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Storage | 10 GB SSD | 20 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

### Software Requirements

| Component | Version |
|-----------|---------|
| Python | 3.12+ |
| Node.js | 20+ |
| PostgreSQL | 15+ |
| Nginx | 1.24+ (if using reverse proxy) |
| Git | 2.40+ |

---

## Docker Deployment

> **Status**: Template — Dockerfiles have not yet been implemented. The following are reference templates to be added to the project.

### Dockerfile — Backend

```dockerfile
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"]
```

### Dockerfile — Frontend

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/frontend.conf /etc/nginx/conf.d/default.conf
```

### docker-compose.yml

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: repoinsight
      POSTGRES_USER: repoinsight
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U repoinsight"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://repoinsight:${POSTGRES_PASSWORD}@db:5432/repoinsight
      SECRET_KEY: ${SECRET_KEY}
      GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID}
      GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET}
      REPOINSIGHT_ENV: production
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./certbot/conf:/etc/letsencrypt
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
```

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-org/repoinsight-ai.git
cd repoinsight-ai

# 2. Create .env file (see Production Environment Variables)
cp .env.example .env
nano .env

# 3. Build and start
docker compose up -d --build

# 4. Run database migrations
docker compose exec backend alembic upgrade head

# 5. Verify
curl http://localhost:8000/health
```

---

## VPS Deployment

Target: Ubuntu 22.04/24.04 LTS

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12, Node.js 20, PostgreSQL 16
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip

curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-16

# Install Nginx and Certbot
sudo apt install -y nginx certbot python3-certbot-nginx

# Verify versions
python3.12 --version
node --version
psql --version
```

### 2. PostgreSQL Database Setup

```bash
sudo -u postgres psql

CREATE USER repoinsight WITH PASSWORD 'your_secure_password';
CREATE DATABASE repoinsight OWNER repoinsight;
GRANT ALL PRIVILEGES ON DATABASE repoinsight TO repoinsight;
\q
```

### 3. Application Setup

```bash
# Create app user
sudo useradd -m -s /bin/bash repoinsight
sudo su - repoinsight

# Clone repository
git clone https://github.com/your-org/repoinsight-ai.git
cd repoinsight-ai

# Backend setup
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cat > .env << 'EOF'
REPOINSIGHT_ENV=production
REPOINSIGHT_SECRET_KEY=your-secret-key-here
REPOINSIGHT_DATABASE_URL=postgresql+asyncpg://repoinsight:your_password@localhost:5432/repoinsight
REPOINSIGHT_GITHUB_CLIENT_ID=your_github_client_id
REPOINSIGHT_GITHUB_CLIENT_SECRET=your_github_client_secret
REPOINSIGHT_CORS_ORIGINS=["https://yourdomain.com"]
EOF

# Run migrations
alembic upgrade head

# Frontend build
cd ../frontend
npm ci
npm run build
# Output: frontend/dist/

exit  # back to root user
```

### 4. Systemd Service — Backend

```bash
sudo tee /etc/systemd/system/repoinsight-backend.service << 'EOF'
[Unit]
Description=RepoInsight AI Backend
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=repoinsight
Group=repoinsight
WorkingDirectory=/home/repoinsight/repoinsight-ai/backend
Environment=PATH=/home/repoinsight/repoinsight-ai/backend/venv/bin:/usr/bin
ExecStart=/home/repoinsight/repoinsight-ai/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now repoinsight-backend
sudo systemctl status repoinsight-backend
```

### 5. Nginx Configuration

See [Nginx Configuration](#nginx-configuration) for the full config file. Summary:

```bash
sudo tee /etc/nginx/sites-available/repoinsight << 'EOF'
# ... full config below ...
EOF

sudo ln -s /etc/nginx/sites-available/repoinsight /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 6. SSL with Certbot

```bash
sudo certbot --nginx -d yourdomain.com
sudo certbot renew --dry-run
```

### 7. Database Backup Cron

```bash
sudo tee /usr/local/bin/repoinsight-backup.sh << 'SCRIPT'
#!/bin/bash
BACKUP_DIR="/var/backups/repoinsight"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
pg_dump -U repoinsight -Fc -f "$BACKUP_DIR/repoinsight_${TIMESTAMP}.dump" repoinsight
find "$BACKUP_DIR" -name "*.dump" -mtime +30 -delete
SCRIPT

sudo chmod +x /usr/local/bin/repoinsight-backup.sh
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/repoinsight-backup.sh
```

---

## Railway Deployment

### Steps

1. **Connect Repository**
   - Go to [railway.app](https://railway.app)
   - Create new project → Deploy from GitHub repo
   - Select the `repoinsight-ai` repository

2. **Add PostgreSQL**
   - In project dashboard → New → Database → PostgreSQL
   - Railway provides `DATABASE_URL` automatically

3. **Configure Backend Service**
   - Service → Settings:
     - **Build Command**: `cd backend && pip install -r requirements.txt`
     - **Start Command**: `cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
     - Railway assigns a dynamic `$PORT` — the app must bind to it

4. **Configure Frontend Service**
   - Add new service from same repo
   - **Build Command**: `cd frontend && npm ci && npm run build`
   - **Start Command**: Use a static file server, e.g., `npx serve frontend/dist -l $PORT`
   - Or deploy as a static site via Railway's Static Site template

5. **Environment Variables**

   Set via Railway dashboard or CLI:

   ```
   REPOINSIGHT_ENV=production
   REPOINSIGHT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
   REPOINSIGHT_GITHUB_CLIENT_ID=<your_client_id>
   REPOINSIGHT_GITHUB_CLIENT_SECRET=<your_client_secret>
   REPOINSIGHT_CORS_ORIGINS=["https://your-app.up.railway.app"]
   REPOINSIGHT_DATABASE_URL=<auto-set-by-postgres-plugin>
   ```

6. **Custom Domain**
   - Settings → Networking → Custom Domain
   - Add `yourdomain.com` and configure DNS CNAME

---

## Render Deployment

### Backend — Web Service

1. Create **Web Service** from GitHub repo
2. Configuration:
   - **Runtime**: Python 3.12
   - **Build Command**: `cd backend && pip install -r requirements.txt && alembic upgrade head`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
3. Environment Variables:
   ```
   REPOINSIGHT_ENV=production
   REPOINSIGHT_SECRET_KEY=<your_secret_key>
   REPOINSIGHT_DATABASE_URL=<your_postgres_url>
   REPOINSIGHT_GITHUB_CLIENT_ID=<your_client_id>
   REPOINSIGHT_GITHUB_CLIENT_SECRET=<your_client_secret>
   REPOINSIGHT_CORS_ORIGINS=["https://yourdomain.com"]
   ```

### Frontend — Static Site

1. Create **Static Site** from the same repo
2. Configuration:
   - **Build Command**: `cd frontend && npm ci && npm run build`
   - **Publish Directory**: `frontend/dist`
3. Environment Variables:
   ```
   REPOINSIGHT_API_URL=https://your-backend.onrender.com
   ```

### Database

- Render provides managed PostgreSQL
- Create from dashboard → New → PostgreSQL
- Copy the Internal Database URL to `REPOINSIGHT_DATABASE_URL`

---

## Nginx Configuration

Full production configuration serving the React SPA and proxying API requests:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com;

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }

    # Certbot ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com;

    # SSL — managed by Certbot
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https://api.github.com;" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;
    gzip_min_length 256;
    gzip_vary on;

    # Frontend static files
    root /home/repoinsight/repoinsight-ai/frontend/dist;
    index index.html;

    # SPA fallback — serve index.html for client-side routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API reverse proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;

        # Timeouts for long-running analysis requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
        access_log off;
    }

    # Deny access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Logging
    access_log /var/log/nginx/repoinsight_access.log;
    error_log /var/log/nginx/repoinsight_error.log;
}
```

---

## SSL/TLS

### Certbot Installation

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Initial Certificate

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### Auto-Renewal

Certbot installs a systemd timer by default. Verify:

```bash
sudo systemctl status certbot.timer
```

Test renewal:

```bash
sudo certbot renew --dry-run
```

Manual renewal cron (if timer is not active):

```bash
sudo crontab -e
# Add: 0 3 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

---

## Production Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REPOINSIGHT_ENV` | Yes | `development` | Application environment: `development` or `production` |
| `REPOINSIGHT_SECRET_KEY` | Yes | — | JWT signing secret. Generate with `openssl rand -hex 32` |
| `REPOINSIGHT_DATABASE_URL` | Yes | — | PostgreSQL connection string. Format: `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `REPOINSIGHT_GITHUB_CLIENT_ID` | Yes | — | GitHub OAuth App client ID |
| `REPOINSIGHT_GITHUB_CLIENT_SECRET` | Yes | — | GitHub OAuth App client secret |
| `REPOINSIGHT_CORS_ORIGINS` | No | `["http://localhost:3000"]` | JSON array of allowed CORS origins |
| `REPOINSIGHT_LOG_LEVEL` | No | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `REPOINSIGHT_DB_ECHO` | No | `false` | Enable SQLAlchemy query logging |
| `REPOINSIGHT_DB_POOL_SIZE` | No | `10` | Connection pool size |
| `REPOINSIGHT_DB_MAX_OVERFLOW` | No | `20` | Max overflow connections beyond pool size |
| `REPOINSIGHT_DB_POOL_TIMEOUT` | No | `30` | Seconds to wait for a connection from the pool |

### Generating Secrets

```bash
# Generate a secure secret key
openssl rand -hex 32

# Generate a random password for PostgreSQL
openssl rand -base64 32
```

---

## Database Backup

### Manual Backup

```bash
# Dump database
pg_dump -U repoinsight -Fc -f repoinsight_$(date +%Y%m%d).dump repoinsight

# Restore from dump
pg_restore -U repoinsight -d repoinsight repoinsight_20260101.dump
```

### Automated Backup Script

```bash
#!/bin/bash
# /usr/local/bin/repoinsight-backup.sh

BACKUP_DIR="/var/backups/repoinsight"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="repoinsight"
DB_USER="repoinsight"

mkdir -p "$BACKUP_DIR"

# Create compressed backup
PGPASSWORD="$DB_PASSWORD" pg_dump \
  -U "$DB_USER" \
  -Fc \
  -f "$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.dump" \
  "$DB_NAME"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "*.dump" -mtime +${RETENTION_DAYS} -delete

# Log
echo "[$(date)] Backup completed: ${DB_NAME}_${TIMESTAMP}.dump" >> /var/log/repoinsight-backup.log
```

### Cron Schedule

```bash
# Run daily at 2 AM
0 2 * * * /usr/local/bin/repoinsight-backup.sh

# Run every 6 hours
0 */6 * * * /usr/local/bin/repoinsight-backup.sh
```

### Remote Backup (S3 / Rclone)

```bash
# Upload to S3
aws s3 cp /var/backups/repoinsight/repoinsight_latest.dump s3://your-bucket/backups/

# Upload with rclone (supports S3, GCS, Dropbox, etc.)
rclone copy /var/backups/repoinsight/ remote:repoinsight-backups/
```

---

## Monitoring

### Health Checks

Backend exposes a health check endpoint:

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

### Uptime Monitoring

Use an external service (UptimeRobot, BetterStack, Checkly) to monitor:

```
GET https://yourdomain.com/health
Expected: 200 OK
Interval: 60 seconds
```

### Log Aggregation

**Backend logs** (stdout/stderr via systemd):

```bash
# View live logs
journalctl -u repoinsight-backend -f

# View last 100 lines
journalctl -u repoinsight-backend -n 100

# View since last boot
journalctl -u repoinsight-backend -b
```

**Nginx logs**:

```bash
# Access log
tail -f /var/log/nginx/repoinsight_access.log

# Error log
tail -f /var/log/nginx/repoinsight_error.log
```

### Structured Logging

The application logs structured JSON in production, suitable for aggregation with:

- **ELK Stack** (Elasticsearch + Logstash + Kibana)
- **Grafana Loki** + Promtail
- **Datadog**
- **Sentry** (error tracking)

### Database Monitoring

```bash
# Check active connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'repoinsight';"

# Check slow queries
sudo -u postgres psql -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds';"

# Table sizes
sudo -u postgres psql -d repoinsight -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```
