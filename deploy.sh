#!/usr/bin/env bash
set -e

APP_DIR="/opt/kino_bot"
SERVICE_NAME="kino-bot"

if [ "$EUID" -ne 0 ]; then
  echo "Iltimos, root yoki sudo bilan ishlating: sudo bash $0"
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git python3 python3-pip python3-venv
fi

mkdir -p "$APP_DIR"
cd "$APP_DIR"

if [ ! -d .git ]; then
  echo "Repository topilmadi. GitHub repo URL ni kiriting (misol: https://github.com/USERNAME/kino_bot_uzb.git)"
  echo "Masalan:"
  echo "git clone https://github.com/egamberdiyovasilbek0-lang/kino_bot_uzb.git ."
  exit 1
fi

git pull --ff-only || true

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Kino Bot Telegram Service
After=network.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
ExecStart=${APP_DIR}/.venv/bin/python3 ${APP_DIR}/bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

sleep 2
systemctl status ${SERVICE_NAME} --no-pager

echo ""
echo "✅ Bot o'rnatildi va xizmatga biriktirildi."
echo "Statusni ko'rish: sudo systemctl status kino-bot"
echo "Loglarni ko'rish: sudo journalctl -u kino-bot -f"
