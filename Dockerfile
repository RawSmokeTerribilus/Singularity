FROM python:3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LD_LIBRARY_PATH=/usr/local/lib

# 1. Arsenal de construcción y dependencias de MakeMKV
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    autoconf \
    automake \
    libtool \
    pkg-config \
    nasm \
    git \
    # Binarios multimedia
    ffmpeg \
    mkvtoolnix \
    mediainfo \
    tor \
    # Dependencias MakeMKV
    libssl-dev \
    libexpat1-dev \
    libgl1-mesa-dev \
    qtbase5-dev \
    zlib1g-dev \
    libavcodec-dev \
    libavutil-dev \
    libavformat-dev \
    libswresample-dev \
    libc6-dev \
    # Herramientas de vida
    nano \
    htop \
    curl \
    python3-dev \
    && apt-get clean

# 2. Instalación de MakeMKV (Usando archivos locales proporcionados)
COPY extras/makemkv-install /tmp/makemkv-install
WORKDIR /tmp/makemkv-install
RUN MAKEMKV_VERSION=1.18.3 && \
    # Build OSS
    cd makemkv-oss-${MAKEMKV_VERSION} && \
    ./configure && \
    make -j$(nproc) && \
    make install && \
    cd .. && \
    # Install BIN
    cd makemkv-bin-${MAKEMKV_VERSION} && \
    mkdir -p tmp && \
    echo "yes" | make install && \
    cd .. && \
    rm -rf /tmp/makemkv-install

# 3. Actualizamos herramientas de Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel cython

WORKDIR /src

# 4. FORJA DE zimg (Estable)
RUN git clone --recursive https://github.com/sekrit-twc/zimg.git && \
    cd zimg && \
    ./autogen.sh && \
    ./configure && \
    make -j$(nproc) && \
    make install && \
    cd .. && rm -rf zimg

# 5. FORJA DE VapourSynth (RELEASE ESTABLE R73)
RUN git clone -b R73 https://github.com/vapoursynth/vapoursynth.git && \
    cd vapoursynth && \
    ./autogen.sh && \
    ./configure && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd .. && rm -rf vapoursynth

WORKDIR /app

# 6. Instalación de librerías de la Suite
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. Despliegue
COPY . .
RUN mkdir -p logs tmp

CMD ["python3", "singularity.py"]
