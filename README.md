# FaceShield Edge Client 📷🍓

Cliente de borda ultraleve de captura de vídeo e despacho de frames para **Raspberry Pi 3 Model B (e superiores)**, integrado com o servidor central **VisionAI FaceShield**.

---

## 💡 Como Funciona

1. **Captura Leve:** Captura frames da câmera conectada à Raspberry Pi (webcam USB ou módulo de câmera oficial).
2. **Detecção de Movimento (0% IA):** Utiliza algoritmo de subtração de frames (*Frame Differencing*) de consumo quase nulo de CPU.
3. **Disparo Inteligente:** Só comprime e envia frames quando alguém se movimentar na frente da câmera, poupando largura de banda da sua rede e recursos da placa.
4. **Despacho via HTTP:** Envia o frame comprimido para a rota `/api/v1/verify` do servidor central, identificando o dispositivo (`device_id`).
5. **Feedback Imediato:** Recebe a resposta do servidor com o nome, ID e nível de confiança da pessoa identificada.

---

## 📋 Pré-requisitos na Raspberry Pi

- Raspberry Pi 3 Model B (ou 3B+, 4, 5) com Raspberry Pi OS instalado.
- Conexão de rede (Wi-Fi ou cabo Ethernet) na mesma rede local do servidor.
- Câmera conectada (Webcam USB ou Módulo de Câmera Oficial).

---

## 🚀 Instalação Rápida (1 Comando)

Clone este repositório na sua Raspberry Pi (exemplo em `/home/pi/pi_client`):

```bash
git clone <URL_DO_GIT_DO_CLIENTE> pi_client
cd pi_client
chmod +x setup.sh
./setup.sh
```

O script `setup.sh` irá:
- Instalar dependências de sistema (`libgl1`, `libglib2.0-0`, etc.).
- Criar o ambiente virtual Python (`venv`).
- Instalar dependências leves (`opencv-python-headless`, `requests`, `python-dotenv`).
- Criar o arquivo `.env`.

---

## ⚙️ Configuração

Abra o arquivo `.env` para ajustar o IP do seu computador/servidor:

```bash
nano .env
```

Ajuste principalmente:

```ini
# Endereço IP do seu computador na rede local onde o servidor FaceShield está rodando
SERVER_URL=http://192.168.1.100:8000/api/v1/verify

# Nome de identificação desta câmera/posto
DEVICE_ID=pi-portaria-01

# Tipo de câmera: 'usb' (webcam) ou 'picamera2' (módulo oficial de fita)
CAMERA_TYPE=usb
```

Salve com `Ctrl + O`, `Enter` e saia com `Ctrl + X`.

---

## 🧪 Teste Manual

Para iniciar e visualizar os logs em tempo real:

```bash
source venv/bin/activate
python main.py
```

Você verá logs como:
```text
2026-09-17 12:30:00 [INFO] FaceShield Edge Client iniciado na Raspberry Pi
2026-09-17 12:30:00 [INFO] Dispositivo: pi-portaria-01
2026-09-17 12:30:00 [INFO] Câmera USB aberta com sucesso.
2026-09-17 12:30:15 [INFO] Enviando frame para o servidor (movimento detectado (área: 5400px), 38.2 KB)...
2026-09-17 12:30:15 [INFO] ✨ [ROSTO] Status: KNOWN | Nome: João Silva (ID: 1) | Conf: 89.40%
```

---

## 🔄 Inicialização Automática no Boot (Serviço Systemd)

Para que o cliente inicie automaticamente ao ligar a Raspberry Pi na tomada:

```bash
# 1. Copie o serviço para o systemd
sudo cp faceshield-client.service /etc/systemd/system/

# 2. Recarregue os daemons
sudo systemctl daemon-reload

# 3. Ative e inicie o serviço
sudo systemctl enable --now faceshield-client

# 4. Verifique o status
sudo systemctl status faceshield-client
```

Para ver os logs do serviço em execução:
```bash
journalctl -u faceshield-client -f
```
