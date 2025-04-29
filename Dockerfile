FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN mkdir -p /run/dbus

# 기본 패키지 설치 + dbus 추가
RUN apt-get update && apt-get install -y --no-install-recommends \
    xfce4 xfce4-terminal \
    tigervnc-standalone-server tigervnc-common tigervnc-tools \
    wget git python3 python3-numpy curl ca-certificates \
    dbus dbus-x11 x11-xserver-utils gnupg lsb-release fonts-nanum locales \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 한글 로케일 설정
RUN sed -i '/^# *ko_KR.UTF-8 UTF-8/s/^# *//' /etc/locale.gen && \
    locale-gen && \
    update-locale LANG=ko_KR.UTF-8

ENV LANG=ko_KR.UTF-8
ENV LANGUAGE=ko_KR:ko
ENV LC_ALL=ko_KR.UTF-8

# /etc/machine-id 생성 (dbus가 필요함)
RUN systemd-machine-id-setup || true

# 아키텍처별 브라우저 설치
ARG TARGETARCH
RUN if [ "$TARGETARCH" = "amd64" ]; then \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/trusted.gpg.d/google.gpg && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable; \
    else \
    apt-get update && \
    apt-get install -y chromium-browser; \
    fi

# noVNC 설치
ENV NOVNC_DIR=/opt/novnc
ENV WEBSOCKIFY_DIR=/opt/novnc/utils/websockify
RUN git clone --depth 1 https://github.com/novnc/noVNC.git $NOVNC_DIR && \
    git clone --depth 1 https://github.com/novnc/websockify.git $WEBSOCKIFY_DIR

# 스타트업 스크립트 복사
COPY scripts/startup.sh /startup.sh
RUN chmod +x /startup.sh

EXPOSE 5901 6080

# 기본 실행
CMD ["/startup.sh"]
