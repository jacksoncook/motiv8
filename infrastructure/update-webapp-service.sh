#!/bin/bash
set -e

echo "Updating motiv8-backend systemd service..."

cat > /tmp/motiv8-backend.service <<'EOF'
[Unit]
Description=motiv8me Web API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/app/motiv8-be
Environment="PATH=/app/motiv8-be/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/app/motiv8-be/.env
ExecStart=/app/motiv8-be/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/motiv8-backend.service /etc/systemd/system/motiv8-backend.service
sudo systemctl daemon-reload
sudo systemctl restart motiv8-backend
sudo systemctl status motiv8-backend --no-pager

echo "Service updated and restarted successfully!"
