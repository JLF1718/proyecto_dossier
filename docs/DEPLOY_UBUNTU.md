# Deploy QA Platform on Ubuntu (Production)

This guide deploys:
- FastAPI backend with Uvicorn on port 8000
- Dash dashboard on port 8050
- Nginx reverse proxy on port 80

## 1. Install OS packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git
```

## 2. Create service user and app directory

```bash
sudo useradd --system --create-home --shell /bin/bash qa || true
sudo mkdir -p /opt/proyecto_dossier
sudo chown -R qa:www-data /opt/proyecto_dossier
```

## 3. Deploy source code

Option A: clone repository directly on server.

```bash
sudo -u qa git clone <REPO_URL> /opt/proyecto_dossier
```

Option B: copy your local workspace into /opt/proyecto_dossier.

## 4. Create Python virtual environment and install dependencies

```bash
cd /opt/proyecto_dossier
sudo -u qa python3 -m venv .venv
sudo -u qa .venv/bin/pip install --upgrade pip
sudo -u qa .venv/bin/pip install -r requirements.txt
```

## 5. Configure environment

```bash
cd /opt/proyecto_dossier
sudo -u qa cp .env.example .env
```

Edit .env and set production values, at minimum:
- DEBUG=false
- SECRET_KEY=<long-random-secret>
- FASTAPI_PORT=8000
- DASH_PORT=8050
- QA_API_BASE=http://127.0.0.1:8000

Optional CORS override in .env:
- ALLOWED_ORIGINS=http://your-domain

## 6. Validate run commands manually

Run exactly the required commands from project root.

Backend:

```bash
cd /opt/proyecto_dossier
sudo -u qa .venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Dashboard:

```bash
cd /opt/proyecto_dossier
sudo -u qa .venv/bin/python dashboard/app.py
```

Stop each command with Ctrl+C after validation.

## 7. Install systemd services

Copy service definitions from repository:
- deploy/systemd/qa_backend.service
- deploy/systemd/qa_dashboard.service

```bash
sudo cp /opt/proyecto_dossier/deploy/systemd/qa_backend.service /etc/systemd/system/qa_backend.service
sudo cp /opt/proyecto_dossier/deploy/systemd/qa_dashboard.service /etc/systemd/system/qa_dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now qa_backend.service
sudo systemctl enable --now qa_dashboard.service
```

Check status:

```bash
sudo systemctl status qa_backend.service --no-pager
sudo systemctl status qa_dashboard.service --no-pager
```

View logs:

```bash
sudo journalctl -u qa_backend.service -f
sudo journalctl -u qa_dashboard.service -f
```

## 8. Configure Nginx reverse proxy

Use the repository template [nginx.conf](../nginx.conf).

```bash
sudo cp /opt/proyecto_dossier/nginx.conf /etc/nginx/sites-available/qa_platform
sudo sed -i 's/server_name qa.example.com;/server_name YOUR_DOMAIN_OR_IP;/' /etc/nginx/sites-available/qa_platform
sudo ln -sf /etc/nginx/sites-available/qa_platform /etc/nginx/sites-enabled/qa_platform
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

## 9. Smoke tests

From server:

```bash
curl -f http://127.0.0.1:8000/api/health
curl -I http://127.0.0.1/
```

From client browser:
- http://YOUR_DOMAIN_OR_IP/ (Dash)
- http://YOUR_DOMAIN_OR_IP/api/docs (FastAPI docs)

## 10. Optional hardening (recommended)

- Configure UFW:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

- Add HTTPS with Let's Encrypt:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_DOMAIN
```

- Rotate logs and backups for data/output folders.

## Update workflow

```bash
cd /opt/proyecto_dossier
sudo -u qa git pull
sudo -u qa .venv/bin/pip install -r requirements.txt
sudo systemctl restart qa_backend.service qa_dashboard.service
sudo systemctl reload nginx
```
