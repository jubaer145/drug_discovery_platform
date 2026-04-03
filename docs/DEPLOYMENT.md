# Production Deployment Guide

> Save this for later. Implement these steps before making the platform publicly accessible.

---

## Security Audit Summary

25 issues found. Must fix before production:

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| 1 | Anthropic API key exposed in `.env` (and git history) | CRITICAL | Rotate key on console.anthropic.com immediately |
| 2 | Default DB password: `secret` | CRITICAL | Change to random 32+ char password |
| 3 | Default MinIO credentials: `minioadmin/minioadmin` | CRITICAL | Change to strong credentials |
| 4 | CORS allows all origins (`*`) | CRITICAL | Restrict to your frontend domain |
| 5 | No authentication on any API endpoint | CRITICAL | Add API key or JWT auth |
| 6 | No rate limiting | CRITICAL | Add slowapi: 10/min on AI, 5/min on pipeline |
| 7 | MinIO running without SSL | HIGH | Enable TLS or use S3 in AWS |
| 8 | No HTTPS anywhere | HIGH | Add ALB with ACM cert or nginx + Let's Encrypt |
| 9 | Docker containers run as root | HIGH | Add `USER appuser` to Dockerfiles |
| 10 | MinIO console exposed (port 9001) | HIGH | Remove port binding in production |
| 11 | Celery Flower exposed (port 5555) | HIGH | Remove port binding or add auth |
| 12 | WebSocket has no authentication | HIGH | Require API key in WS handshake |
| 13 | File download endpoint — path traversal risk | HIGH | Validate bucket names, reject `..` |
| 14 | `.env` file has 777 permissions | MEDIUM | `chmod 600 .env` |
| 15 | Redis running without password | MEDIUM | Add `requirepass` config |
| 16 | No CSRF protection | MEDIUM | Add CSRF tokens for state-changing ops |
| 17 | No request logging/audit trail | MEDIUM | Log access with IP, user, endpoint |
| 18 | `--reload` flag in production compose | LOW | Remove for production |

---

## Code Changes Required

### 1. Add API Key Authentication

Create `backend/core/auth.py`:
```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader
from core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def require_api_key(api_key: str = Security(api_key_header)):
    if not api_key or api_key not in settings.api_keys:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key
```

Add to `config.py`:
```python
api_keys: list[str] = []  # Loaded from API_KEYS env var (comma-separated)
```

### 2. Restrict CORS

```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),  # e.g., "https://yourdomain.com"
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)
```

### 3. Add Rate Limiting

```bash
pip install slowapi
```

```python
# backend/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# On expensive endpoints:
@router.post("/suggest-targets")
@limiter.limit("10/minute")
async def suggest_targets(request: Request, ...):
```

### 4. Secure File Downloads

```python
# backend/main.py
ALLOWED_BUCKETS = {"structures", "molecules", "results"}

@app.get("/api/files/{bucket}/{path:path}")
async def download_file_endpoint(bucket: str, path: str):
    if bucket not in ALLOWED_BUCKETS:
        raise HTTPException(status_code=403, detail="Bucket not allowed")
    if ".." in path:
        raise HTTPException(status_code=403, detail="Path traversal not allowed")
    ...
```

### 5. Non-Root Docker

Add to `backend/Dockerfile`:
```dockerfile
RUN useradd -m -u 1000 appuser
USER appuser
```

---

## AWS Deployment Architecture

```
                Internet
                   |
            [Route 53 - DNS]
                   |
            [ACM Certificate - HTTPS]
                   |
            [ALB - Application Load Balancer]
               /         \
        [Target Group]  [Target Group]
         /                    \
   [ECS Service]         [ECS Service]
    Frontend              Backend + Celery
       |                      |
   [ECR Image]           [ECR Image]
                              |
                    [ElastiCache Redis]
                    [RDS PostgreSQL]
                    [S3 Bucket (replaces MinIO)]
```

### AWS Services & Estimated Costs

| Service | Purpose | Monthly Cost |
|---------|---------|-------------|
| ECS Fargate (2 services) | Run containers | ~$30-50 |
| ALB | Load balancer + HTTPS | ~$20 |
| RDS PostgreSQL (db.t3.micro) | Managed database | ~$15 |
| ElastiCache Redis (cache.t3.micro) | Managed Redis | ~$15 |
| S3 | File storage (replaces MinIO) | ~$1 |
| ECR | Docker image registry | ~$1 |
| ACM | SSL/TLS certificate | Free |
| Route 53 | DNS | ~$1 |
| Secrets Manager | API keys | ~$1 |
| **Total** | | **~$85-105/month** |

### Budget Alternative: Single EC2

| Service | Purpose | Monthly Cost |
|---------|---------|-------------|
| EC2 t3.medium (2 vCPU, 4GB) | All services via docker compose | ~$30 |
| Let's Encrypt | SSL certificate | Free |
| Route 53 | DNS | ~$1 |
| **Total** | | **~$31/month** |

---

## Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    environment:
      - UV_PROJECT_ENVIRONMENT=/opt/venv
    env_file: .env.prod
    depends_on: [postgres, redis, minio]
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
    networks: [drug-discovery-net]
    restart: always
    # NO ports exposed — nginx handles external traffic

  frontend:
    build: ./frontend
    env_file: .env.prod
    command: npm start
    networks: [drug-discovery-net]
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./certbot/conf:/etc/letsencrypt
    depends_on: [backend, frontend]
    networks: [drug-discovery-net]
    restart: always

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: drugdiscovery
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: [postgres_data:/var/lib/postgresql/data]
    networks: [drug-discovery-net]
    restart: always
    # NO ports exposed externally

  redis:
    image: redis:7
    command: redis-server --requirepass ${REDIS_PASSWORD}
    networks: [drug-discovery-net]
    restart: always

  minio:
    image: minio/minio
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    command: server /data
    volumes: [minio_data:/data]
    networks: [drug-discovery-net]
    restart: always
    # NO console port exposed

  celery_worker:
    build: ./backend
    env_file: .env.prod
    environment:
      - UV_PROJECT_ENVIRONMENT=/opt/venv
    command: celery -A core.queue worker --loglevel=info --concurrency=4
    depends_on: [redis, postgres]
    networks: [drug-discovery-net]
    restart: always

networks:
  drug-discovery-net:
    driver: bridge

volumes:
  postgres_data:
  minio_data:
```

---

## Nginx Config

Create `nginx/nginx.conf`:

```nginx
events { worker_connections 1024; }

http {
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Rate limiting zone
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;

    upstream frontend { server frontend:3000; }
    upstream backend { server backend:8000; }

    server {
        listen 80;
        server_name yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name yourdomain.com;

        ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
        }

        # API
        location /api/ {
            limit_req zone=api burst=10 nodelay;
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # WebSocket
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Health check (no rate limit)
        location /health {
            proxy_pass http://backend;
        }
    }
}
```

---

## Deployment Steps (EC2 single-server)

```bash
# 1. Launch EC2 t3.medium with Ubuntu 22.04
# 2. SSH in and install Docker + Docker Compose
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER

# 3. Clone repo
git clone https://github.com/jubaer145/drug_discovery_platform.git
cd drug_discovery_platform

# 4. Create production .env
cp .env.example .env.prod
# Edit .env.prod with strong passwords and real API key

# 5. Get SSL certificate
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com

# 6. Start production stack
docker compose -f docker-compose.prod.yml up -d --build

# 7. Verify
curl https://yourdomain.com/health
```

---

## Pre-Deployment Checklist

- [ ] Anthropic API key rotated (old one is compromised)
- [ ] `.env` added to `.gitignore`
- [ ] Strong passwords set for PostgreSQL, MinIO, Redis
- [ ] CORS restricted to your domain
- [ ] API key authentication enabled
- [ ] Rate limiting enabled
- [ ] HTTPS/SSL configured
- [ ] Management ports not exposed (MinIO console, Flower, Redis)
- [ ] Docker containers run as non-root
- [ ] `--reload` removed from production command
- [ ] Domain name configured in Route 53 / DNS
- [ ] SSL certificate obtained (Let's Encrypt or ACM)
- [ ] Monitoring set up (CloudWatch or similar)
