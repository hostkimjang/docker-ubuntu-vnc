#!/bin/bash

apk update && apk add ca-certificates wget && update-ca-certificates
# apt-get update && apt-get -y upgrade

# 네트워크 연결 확인 함수
check_network() {
    echo "네트워크 연결 테스트..."
    for i in {1..5}; do
        if ping -c 1 -t 5 1.1.1.1 & > /dev/null; then
        echo "기본 네트워크 연결 성공"
        return 0
    fi
    echo "네트워크 연결 시도 $i/5 실패, 재시도 중..."
    sleep 5
    done
    echo "네트워크 연결 실패"
    return 1
}

# 기본 네트워크 연결 확인
check_network || { echo "인터넷 연결 없음. 종료합니다."; exit 1; }

# Cloudflare GPG 키 추가 (타임아웃 설정)
echo "Cloudflare GPG 키 다운로드..."
if wget --timeout=30 --quiet https://pkg.cloudflareclient.com/pubkey.gpg -O /tmp/cloudflare.gpg; then
    gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg /tmp/cloudflare.gpg
else
    echo "Cloudflare 키 다운로드 실패. 네트워크 문제가 있을 수 있습니다."
    exit 1
fi

# Warp 서비스 직접 실행 및 백그라운드 유지
echo "Starting WARP service..."
nohup /bin/warp-svc > /dev/null 2>&1 &

# 서비스가 시작될 때까지 기다림
echo "Waiting for WARP service to start..."
sleep 5

# Warp 등록 및 연결
echo "Registering WARP client..."
warp-cli --accept-tos registration new
sleep 5
echo "Connecting to WARP..."
yes | warp-cli --accept-tos connect
sleep 5
echo "Setting WARP mode..."
warp-cli --accept-tos mode warp+doh
sleep 5

# 연결 확인
echo "Checking connection..."
curl https://www.cloudflare.com/cdn-cgi/trace/

# 컨테이너가 종료되지 않도록 무한 대기
echo "WARP is running. Keeping container alive..."
# tail -f /dev/null

