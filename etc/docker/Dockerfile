FROM python:3.8-slim as package_step

# Instala bibliotecas do sistema necessárias para o OpenCV e ferramentas de compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ninja-build \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libglib2.0-0 \
    libgl1-mesa-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/hikvision

COPY ./requirements.txt .
COPY ./src ./src

# Atualiza pip
RUN pip install --upgrade pip

# Instala dependências
RUN pip install requests
RUN pip install -r requirements.txt

WORKDIR /opt/hikvision/src

