"""Carga perezosa de los modelos: YOLO11 (SKU-110K) para detectar y CLIP para reconocer."""
import threading

from django.conf import settings

_lock = threading.Lock()
_yolo = None
_clip = None
_owl = None


class MLUnavailable(Exception):
    """No se pudo cargar un modelo (falta la librería, el archivo o la descarga)."""


def get_yolo():
    global _yolo
    if _yolo is None:
        with _lock:
            if _yolo is None:
                path = settings.YOLO_MODEL_PATH
                if not path.is_file():
                    raise MLUnavailable(f'No se encontró el modelo YOLO en {path}.')
                try:
                    from ultralytics import YOLO
                    _yolo = YOLO(str(path))
                except Exception as e:
                    raise MLUnavailable(f'No se pudo cargar YOLO: {e}') from e
    return _yolo


def get_clip():
    global _clip
    if _clip is None:
        with _lock:
            if _clip is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    _clip = SentenceTransformer(settings.CLIP_MODEL_NAME)
                except Exception as e:
                    raise MLUnavailable(f'No se pudo cargar CLIP: {e}') from e
    return _clip


def get_owl():
    """OWLv2 (detector de objetos sin clases): propone cajas de cualquier objeto."""
    global _owl
    if _owl is None:
        with _lock:
            if _owl is None:
                try:
                    from transformers import Owlv2ForObjectDetection, Owlv2Processor
                    nombre = settings.OWL_MODEL_NAME
                    _owl = (Owlv2Processor.from_pretrained(nombre),
                            Owlv2ForObjectDetection.from_pretrained(nombre).eval())
                except Exception as e:
                    raise MLUnavailable(f'No se pudo cargar OWLv2: {e}') from e
    return _owl


def propose_objects(imagen, min_objectness=0.12, iou=0.3):
    """Cajas (x1, y1, x2, y2) y puntaje de "objeto" de cualquier cosa en la imagen."""
    import torch
    from torchvision.ops import nms
    procesador, modelo = get_owl()
    ancho, alto = imagen.size
    lado = max(ancho, alto)  # OWLv2 rellena la imagen hasta hacerla cuadrada
    with torch.no_grad():
        salida = modelo(**procesador(text=[['a product']], images=imagen, return_tensors='pt'))
    objeto = salida.objectness_logits.sigmoid()[0]
    cx, cy, w, h = salida.pred_boxes[0].unbind(-1)
    cajas = torch.stack([(cx - w / 2) * lado, (cy - h / 2) * lado,
                         (cx + w / 2) * lado, (cy + h / 2) * lado], dim=-1)
    cajas[:, 0::2] = cajas[:, 0::2].clamp(0, ancho)
    cajas[:, 1::2] = cajas[:, 1::2].clamp(0, alto)
    ok = objeto > min_objectness
    cajas, objeto = cajas[ok], objeto[ok]
    keep = nms(cajas, objeto, iou)
    return cajas[keep].round().int().tolist(), objeto[keep].tolist()


def _normalizar(vector):
    import numpy as np
    v = np.asarray(vector, dtype='float32')
    norma = np.linalg.norm(v)
    return v / norma if norma else v


def embed_image(source):
    """Embedding CLIP normalizado (lista de floats) de una ruta o imagen PIL."""
    from PIL import Image
    imagen = Image.open(source) if isinstance(source, (str, bytes)) or hasattr(source, '__fspath__') else source
    imagen = imagen.convert('RGB')
    vector = get_clip().encode(imagen)
    return _normalizar(vector).tolist()


def embed_images(imagenes, batch_size=32):
    """Embeddings normalizados de una lista de imágenes PIL (en lotes)."""
    import numpy as np
    if not imagenes:
        return np.zeros((0, 0), dtype='float32')
    vectores = get_clip().encode(
        [i.convert('RGB') for i in imagenes], batch_size=batch_size)
    vectores = np.asarray(vectores, dtype='float32')
    normas = np.linalg.norm(vectores, axis=1, keepdims=True)
    normas[normas == 0] = 1
    return vectores / normas
