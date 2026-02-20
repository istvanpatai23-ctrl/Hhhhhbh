FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Alapvető Linux csomagok és fordítók telepítése a zsign-hoz
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    uuid-dev \
    zip \
    unzip \
    curl \
    git \
    cmake \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Zsign letöltése és lefordítása CMake segítségével
RUN git clone https://github.com/zhlynn/zsign.git /tmp/zsign \
    && cd /tmp/zsign \
    && cmake . \
    && make \
    && cp zsign /usr/local/bin/ \
    && rm -rf /tmp/zsign

# A mi projektünk beállítása
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Másoljuk a többi fájlt
COPY . .

# Futtatás
EXPOSE 10000
CMD ["python3", "app.py"]
