#!/bin/bash
# ==============================================================
# Script Instalasi SUKU-Monitor di VPS Ubuntu (Jalankan di VPS Anda)
# ==============================================================
set -e

echo "=== 1. Update Sistem & Install Paket Dasar ==="
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip git curl nginx

echo "=== 2. Clone Repositori SUKU-Monitor ==="
if [ -d "downloader" ]; then
    cd downloader && git pull origin main
else
    git clone https://github.com/hrztsquad/downloader.git
    cd downloader
fi

echo "=== 3. Setup Virtualenv Python & Dependensi ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== 4. Salin Konfigurasi .env ==="
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[PERHATIAN] File .env telah dibuat dari .env.example. Silakan periksa kredensialnya jika diperlukan."
fi

echo "=== 5. Inisialisasi Database ==="
python3 -c "from app.models.database import init_db; init_db(); print('Database OK!')"

echo "=== 6. Setup Systemd Service (Agar Jalan Otomatis di Background) ==="
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

sudo bash -c "cat << 'SERVICE' > /etc/systemd/system/suku-monitor.service
[Unit]
Description=SUKU-Monitor - UIN Sunan Kudus Monitoring Service
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python3 $CURRENT_DIR/run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE"

sudo systemctl daemon-reload
sudo systemctl enable suku-monitor
sudo systemctl restart suku-monitor

echo "=== 7. Status Service ==="
sudo systemctl status suku-monitor --no-pager

echo ""
echo "=========================================================="
echo "SUKU-Monitor berhasil di-deploy!"
echo "Akses dashboard di browser: http://$(curl -s ifconfig.me):8000"
echo "=========================================================="
