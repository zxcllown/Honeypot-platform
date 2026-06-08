FROM ubuntu:24.04

RUN apt update && apt install -y --no-install-recommends \
    bash \
    coreutils \
    findutils \
    grep \
    sed \
    gawk \
    curl \
    wget \
    net-tools \
    iproute2 \
    iputils-ping \
    procps \
    python3 \
    ca-certificates \
    strace \
    netcat-openbsd \
    zsh \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /sandbox


RUN useradd -m sandboxuser
USER sandboxuser

CMD ["/bin/bash"]