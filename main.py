"""Cliente Edge de Captura e Envio Inteligente para Raspberry Pi 3B.

Captura frames da câmera local, detecta movimento de forma ultraleve
e despacha frames para o servidor central de reconhecimento facial.
"""

import logging
import signal
import sys
import time
from typing import Optional, Tuple

import cv2
import numpy as np
import requests

import config

# Configuração de logging limpo para terminal e systemd
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pi_client")


class MotionDetector:
    """Detector de movimento ultraleve por subtração de frames (0% IA).

    Consome frações mínimas de CPU na Raspberry Pi 3B.
    """

    def __init__(self, threshold: int = 25, min_area: int = 3000):
        self.threshold = threshold
        self.min_area = min_area
        self.prev_gray: Optional[np.ndarray] = None

    def detect(self, frame: np.ndarray) -> Tuple[bool, int]:
        """Retorna se houve movimento e a área estimada de variação."""
        # Reduz resolução para análise de movimento ultrarrápida
        small = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_NEAREST)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_gray is None:
            self.prev_gray = gray
            return False, 0

        # Diferença absoluta entre o frame atual e o anterior
        delta = cv2.absdiff(self.prev_gray, gray)
        thresh = cv2.threshold(delta, self.threshold, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        total_motion_area = sum(cv2.contourArea(c) for c in contours)

        # Atualiza o fundo com suavização leve (média ponderada)
        cv2.accumulateWeighted(gray, self.prev_gray.astype(np.float32), 0.1)
        self.prev_gray = np.uint8(self.prev_gray)

        has_motion = total_motion_area >= self.min_area
        return has_motion, int(total_motion_area)


class CameraCapture:
    """Gerencia a captura da câmera (USB V4L2 ou Picamera2)."""

    def __init__(self):
        self.cap = None
        self.picam2 = None
        self._init_camera()

    def _init_camera(self):
        if config.CAMERA_TYPE == "picamera2":
            try:
                from picamera2 import Picamera2

                logger.info("Inicializando Picamera2 (Módulo de Câmera Oficial)...")
                self.picam2 = Picamera2()
                camera_config = self.picam2.create_video_configuration(
                    main={"size": (config.FRAME_WIDTH, config.FRAME_HEIGHT), "format": "RGB888"}
                )
                self.picam2.configure(camera_config)
                self.picam2.start()
                logger.info("Picamera2 iniciada com sucesso.")
                return
            except Exception as e:
                logger.warning(f"Falha ao iniciar Picamera2 ({e}). Tentando OpenCV USB...")

        # Fallback ou padrão USB
        logger.info(f"Abrindo câmera USB (índice {config.CAMERA_INDEX})...")
        self.cap = cv2.VideoCapture(config.CAMERA_INDEX)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, config.FPS_TARGET)

        if not self.cap.isOpened():
            logger.error(f"Não foi possível abrir a câmera USB no índice {config.CAMERA_INDEX}.")
        else:
            logger.info("Câmera USB aberta com sucesso.")

    def read_frame(self) -> Optional[np.ndarray]:
        if self.picam2 is not None:
            try:
                frame_rgb = self.picam2.capture_array()
                return cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            except Exception as e:
                logger.error(f"Erro na leitura do Picamera2: {e}")
                return None

        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                return frame
        return None

    def release(self):
        if self.picam2 is not None:
            try:
                self.picam2.stop()
            except Exception:
                pass
        if self.cap is not None:
            self.cap.release()


class EdgeClient:
    """Cliente principal: orquestra captura, detecção de movimento e envio."""

    def __init__(self):
        self.running = True
        self.camera = CameraCapture()
        self.detector = MotionDetector(
            threshold=config.MOTION_THRESHOLD,
            min_area=config.MOTION_MIN_AREA,
        )
        self.session = requests.Session()
        self.last_sent_time = 0.0
        self.last_periodic_time = 0.0

        # Tratamento de interrupção (Ctrl+C / SIGTERM do systemd)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        logger.info(f"Sinal de parada recebido ({signum}). Encerrando cliente...")
        self.running = False

    def send_frame(self, frame: np.ndarray, reason: str = "motion") -> bool:
        """Comprime o frame em JPEG e envia via POST para o servidor."""
        now = time.time()
        if now - self.last_sent_time < config.COOLDOWN_SECONDS:
            return False  # Cooldown ativo

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), config.JPEG_QUALITY]
        success, encoded_img = cv2.imencode(".jpg", frame, encode_params)
        if not success:
            logger.error("Falha ao codificar frame para JPEG.")
            return False

        jpeg_bytes = encoded_img.tobytes()
        self.last_sent_time = now

        try:
            files = {"file": ("frame.jpg", jpeg_bytes, "image/jpeg")}
            data = {"device_id": config.DEVICE_ID, "source": f"pi:{config.DEVICE_ID}"}

            logger.info(f"Enviando frame para o servidor ({reason}, {len(jpeg_bytes)/1024:.1f} KB)...")
            res = self.session.post(
                config.SERVER_URL,
                files=files,
                data=data,
                timeout=config.REQUEST_TIMEOUT,
            )

            if res.status_code == 200:
                body = res.json()
                faces = body.get("faces_detected", 0)
                results = body.get("results", [])

                if faces == 0:
                    logger.info("Servidor analisou: nenhum rosto detectado no frame.")
                else:
                    for r in results:
                        status = r.get("status")
                        name = r.get("display_name", "Desconhecido")
                        pid = r.get("person_id")
                        conf = r.get("confidence", 0.0)
                        logger.info(
                            f"✨ [ROSTO] Status: {status.upper()} | Nome: {name} (ID: {pid}) | Conf: {conf:.2%}"
                        )
                return True
            else:
                logger.warning(f"Servidor retornou erro HTTP {res.status_code}: {res.text[:200]}")
                return False

        except requests.exceptions.ConnectionError:
            logger.error(f"Não foi possível conectar ao servidor em {config.SERVER_URL}. Verifique a rede.")
            return False
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout na conexão com o servidor ({config.REQUEST_TIMEOUT}s).")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar frame: {e}")
            return False

    def run(self):
        logger.info("=====================================================")
        logger.info(f"FaceShield Edge Client iniciado na Raspberry Pi")
        logger.info(f"Dispositivo: {config.DEVICE_ID}")
        logger.info(f"Servidor alvo: {config.SERVER_URL}")
        logger.info(f"Detecção de movimento: {'ATIVA' if config.MOTION_DETECTION_ENABLED else 'DESATIVADA'}")
        logger.info(f"Cooldown entre envios: {config.COOLDOWN_SECONDS}s")
        logger.info("=====================================================")

        frame_interval = 1.0 / max(1, config.FPS_TARGET)

        while self.running:
            loop_start = time.time()

            frame = self.camera.read_frame()
            if frame is None:
                time.sleep(0.5)
                continue

            now = time.time()
            trigger_send = False
            trigger_reason = ""

            # 1. Verificação por detecção de movimento
            if config.MOTION_DETECTION_ENABLED:
                has_motion, motion_area = self.detector.detect(frame)
                if has_motion:
                    trigger_send = True
                    trigger_reason = f"movimento detectado (área: {motion_area}px)"
            else:
                # Se detecção estiver desativada, opera por envio contínuo respeitando o cooldown
                trigger_send = True
                trigger_reason = "contínuo"

            # 2. Verificação periódica opcional (heartbeat)
            if (
                not trigger_send
                and config.PERIODIC_INTERVAL_SECONDS > 0
                and (now - self.last_periodic_time >= config.PERIODIC_INTERVAL_SECONDS)
            ):
                trigger_send = True
                trigger_reason = "periódico (heartbeat)"
                self.last_periodic_time = now

            # Disparo do frame
            if trigger_send:
                self.send_frame(frame, reason=trigger_reason)

            # Controle da taxa de quadros (FPS) para não fritar a CPU do Pi 3
            elapsed = time.time() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        # Finalização limpa
        logger.info("Encerrando câmera e conexões...")
        self.camera.release()
        self.session.close()
        logger.info("Cliente encerrado com sucesso.")


if __name__ == "__main__":
    client = EdgeClient()
    client.run()
