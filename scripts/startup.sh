#!/bin/bash
set -e

CONTAINER_NAME=${CONTAINER_NAME:-crawler}

# # dbus 서비스 시작 (백그라운드)
# dbus-daemon --system --fork
# unset DBUS_SESSION_BUS_ADDRESS

# VNC 비밀번호 설정
mkdir -p /root/.vnc
echo "${VNC_PW:-password}" | vncpasswd -f > /root/.vnc/passwd
chmod 600 /root/.vnc/passwd

# VNC 서버 시작
vncserver :1 -geometry 1920x1080 -depth 24
sleep 2

export DISPLAY=:1

# 브라우저 자동 실행
# if command -v google-chrome-stable >/dev/null 2>&1; then
#   google-chrome-stable --no-sandbox --disable-gpu --disable-dev-shm-usage --disable-notifications --disable-popup-blocking --no-first-run --disable-fre --no-default-browser-check --window-size=1280,720 https://www.google.com &
# elif command -v chromium-browser >/dev/null 2>&1; then
#   ungoogled-chromium --no-sandbox --disable-gpu --disable-dev-shm-usage --disable-notifications --disable-popup-blocking --no-first-run --disable-fre --no-default-browser-check --window-size=1280,720 https://www.google.com &
# fi

# noVNC 서버 시작
cd /opt/novnc
./utils/novnc_proxy --vnc localhost:5901 &

cd /
chmod +x ./cloudflare_setup.sh
./cloudflare_setup.sh

sleep 5

echo "[${CONTAINER_NAME}] 🚀 크롤러 실행"
pip3 install -r /app/requirment.txt
chmod +x /app/run.py
python3 /app/run.py "$START_INDEX" "$END_INDEX"

# cd /
# if [ -f "./run.sh" ]; then
#     chmod +x ./run.sh
#     ./run.sh
# elif [ -f "./run.py" ]; then
#     echo "Starting Python script..."
#     python3 ./run.py
# fi