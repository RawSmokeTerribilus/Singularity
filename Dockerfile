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
    pciutils \
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

# --- 4. FORJA DE ZIMG (Virtud y Excelencia) ---
RUN git clone --recursive https://github.com/sekrit-twc/zimg.git /tmp/zimg && \
    cd /tmp/zimg && \
    ./autogen.sh && \
    ./configure --prefix=/usr/local --enable-simd && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/zimg

# 5. FORJA DE VapourSynth (RELEASE ESTABLE R73)
RUN git clone -b R73 https://github.com/vapoursynth/vapoursynth.git && \
    cd vapoursynth && \
    ./autogen.sh && \
    ./configure && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd .. && rm -rf vapoursynth

# --- 6. HERRAMIENTAS DE CONSTRUCCIÓN Y MÚSCULOS ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    meson \
    ninja-build \
    pkg-config \
    libxxhash-dev \
    libavformat-dev \
    libavcodec-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libass-dev && \
    rm -rf /var/lib/apt/lists/*

# --- 7. FORJA DE L-SMASH (Librería Base - El Yunque) ---
# Necesaria para que el plugin tenga donde apoyarse
RUN git clone https://github.com/l-smash/l-smash.git /tmp/l-smash && \
    cd /tmp/l-smash && \
    ./configure --prefix=/usr --enable-shared && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/l-smash

# --- 12. FORJA DE L-SMASH WORKS (Fijación de Binario) ---
RUN git clone https://github.com/oatssss/L-SMASH-Works.git /tmp/lsmas-plugin && \
    cd /tmp/lsmas-plugin && \
    # Parche de flags para FFmpeg 5/6
    sed -i '1s/^/#define AV_FRAME_FLAG_INTERLACED (1 << 0)\n#define AV_FRAME_FLAG_TOP_FIELD_FIRST (1 << 1)\n/' common/video_output.h && \
    cd VapourSynth && \
    sed -i '1s/^/#include <strings.h>\n/' video_output.c && \
    ./configure --prefix=/usr/local --extra-cflags="-I/usr/local/include" --extra-ldflags="-L/usr/local/lib" && \
    make -j$(nproc) && \
    mkdir -p /usr/local/lib/vapoursynth && \
    # Usamos comodín para pillar 'libvslsmashsource.so.942' y renombrarlo correctamente
    cp libvslsmashsource.so* /usr/local/lib/vapoursynth/vslsmashsource.so && \
    ldconfig && \
    rm -rf /tmp/lsmas-plugin

# 1. Habilitamos contrib, non-free y non-free-firmware (Formato nuevo y viejo)
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's/Components: main/Components: main contrib non-free non-free-firmware/g' /etc/apt/sources.list.d/debian.sources; \
    else \
        sed -i 's/main$/main contrib non-free non-free-firmware/g' /etc/apt/sources.list; \
    fi && \
    apt-get update && apt-get install -y \
    mesa-va-drivers \
    intel-media-va-driver-non-free \
    libva-drm2 \
    vainfo \
    && rm -rf /var/lib/apt/lists/*

# Variable de entorno de seguridad (luego el Agente la puede pisar)
ENV MOZ_X11_EGL=1

# --- 9. ENTORNO DE TRABAJO ---
WORKDIR /app

# 9. Instalación de librerías de la Suite
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Ajustamos la propiedad de la carpeta de la app para nuestro usuario 1000
RUN chown -R 1000:1000 /app

# 10. Despliegue
COPY --chown=1000:1000 . .
RUN mkdir -p logs tmp core/templates && chown -R 1000:1000 /app

CMD ["python3", "singularity.py"]
