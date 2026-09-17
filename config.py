"""Configurações do cliente Edge para Raspberry Pi 3B."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env do mesmo diretório se existir
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key, "").strip().lower()
    if not val:
        return default
    return val in ("1", "true", "yes", "on", "sim")


# ── Servidor Central ──────────────────────────────────────────────────────────
SERVER_URL = os.getenv("SERVER_URL", "http://192.168.1.100:8000/api/v1/verify")
DEVICE_ID = os.getenv("DEVICE_ID", "pi-camera-01")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "6.0"))

# ── Configurações de Câmera ───────────────────────────────────────────────────
# Tipo: "usb" (Webcam padrão V4L2) ou "picamera2" (Módulo oficial Raspberry Pi)
CAMERA_TYPE = os.getenv("CAMERA_TYPE", "usb").lower()
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", "640"))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT", "480"))
FPS_TARGET = int(os.getenv("FPS_TARGET", "10"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "80"))

# ── Detecção de Movimento & Disparo Inteligente ────────────────────────────────
# Se ativado, analisa movimento e só despacha foto se houver alguém na frente.
# Isso reduz drasticamente uso de rede e carga no Raspberry Pi 3B.
MOTION_DETECTION_ENABLED = get_bool("MOTION_DETECTION_ENABLED", True)
MOTION_THRESHOLD = int(os.getenv("MOTION_THRESHOLD", "25"))
MOTION_MIN_AREA = int(os.getenv("MOTION_MIN_AREA", "3000"))

# Cooldown (em segundos) entre envios ao servidor (evita flood da mesma pessoa)
COOLDOWN_SECONDS = float(os.getenv("COOLDOWN_SECONDS", "2.0"))

# Se > 0, envia um frame a cada N segundos mesmo se não houver movimento detectado
PERIODIC_INTERVAL_SECONDS = float(os.getenv("PERIODIC_INTERVAL_SECONDS", "0.0"))
