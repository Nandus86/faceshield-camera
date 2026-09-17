#!/usr/bin/env bash
# ==============================================================================
# Script de Instalação Automatizado do FaceShield Edge Client
# Otimizado para Raspberry Pi 3 Model B (Raspberry Pi OS / Debian)
# ==============================================================================

set -e

echo "=========================================================="
echo "🛡️  Instalando FaceShield Edge Client na Raspberry Pi..."
echo "=========================================================="

# 1. Dependências do sistema operacional
echo "-> Atualizando repositórios e instalando dependências de sistema..."
sudo apt-get update -y
sudo apt-get install -y python3-pip python3-venv python3-dev libgl1 libglib2.0-0 v4l-utils

# 2. Criação do ambiente virtual isolado (recomendado no Debian/Raspberry Pi OS)
if [ ! -d "venv" ]; then
    echo "-> Criando ambiente virtual Python (venv)..."
    python3 -m venv venv
else
    echo "-> Ambiente virtual (venv) já existe."
fi

# 3. Instalação das dependências Python
echo "-> Instalando pacotes Python..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Arquivo de configuração .env
if [ ! -f ".env" ]; then
    echo "-> Criando arquivo de configuração .env a partir de .env.example..."
    cp .env.example .env
    echo "⚠️  ATENÇÃO: Edite o arquivo .env com o IP do seu servidor central!"
    echo "   Exemplo: nano .env"
fi

echo "=========================================================="
echo "✅ Instalação concluída com sucesso!"
echo ""
echo "Para rodar em modo de teste:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "Para instalar como serviço de inicialização automática no boot:"
echo "   sudo cp faceshield-client.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable --now faceshield-client"
echo "=========================================================="
