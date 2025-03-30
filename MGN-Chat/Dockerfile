FROM python:3.10

RUN apt-get update && \
    apt-get install -y \
    libmtdev-dev \
    libgl1-mesa-glx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos necessários para o container
COPY . /app

# Instala as dependências
RUN pip install --no-cache-dir kivy pyzmq

RUN apt update && apt install -y xclip xsel

RUN xhost +SI:localuser:root  


# Expondo a porta do servidor ZMQ
EXPOSE 5555
EXPOSE 5556


