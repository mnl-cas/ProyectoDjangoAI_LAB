"""Análisis de estanterías.

Flujo: proponer cajas (OWLv2 + YOLO SKU-110K) → recortar cada caja → compararla con las
fotos de referencia usando CLIP → quedarse con las coincidencias claras → contar por producto.
"""
import io
from collections import Counter

import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont, ImageOps

from catalog.models import Product, ReferenceImage
from inventory.models import Alert, StockMovement
from inventory.services import apply_movement

from .ml import MLUnavailable, embed_images, get_yolo, propose_objects
from .models import Inspection, InspectionItem

MAX_SIDE = 1600   # se reduce la foto para que el análisis sea rápido
MAX_CROPS = 150   # tope de recortes por foto para no saturar a CLIP
MIN_AREA = 0.0015  # una caja debe cubrir al menos 0.15 % de la foto


# ---------- Referencias ----------

def reference_vectors(imagen):
    """Embeddings de una foto de referencia: completa, recorte del objeto y su espejo."""
    imagen = ImageOps.exif_transpose(imagen).convert('RGB')
    imagenes = [imagen]
    try:
        cajas, puntajes = propose_objects(imagen)
        ancho, alto = imagen.size
        candidatas = [(p, c) for c, p in zip(cajas, puntajes)
                      if 0.03 < (c[2] - c[0]) * (c[3] - c[1]) / (ancho * alto) < 0.85]
        if candidatas:
            recorte = imagen.crop(max(candidatas)[1])
            imagenes += [recorte, ImageOps.mirror(recorte)]
    except MLUnavailable:
        pass  # sin OWLv2 se usa solo la foto completa
    return embed_images(imagenes).tolist()


def _referencias():
    """Matriz de embeddings de referencia y el producto dueño de cada fila."""
    vectores, duenos = [], []
    for ref in ReferenceImage.objects.exclude(embedding__isnull=True):
        emb = ref.embedding
        if emb and not isinstance(emb[0], list):  # formato antiguo: un solo vector
            emb = [emb]
        for v in emb or []:
            vectores.append(v)
            duenos.append(ref.product_id)
    if not vectores:
        return None, np.array([])
    return np.asarray(vectores, dtype='float32'), np.asarray(duenos)


# ---------- Cajas ----------

def _yolo_boxes(imagen):
    """Cajas de YOLO11 entrenado en SKU-110K (muy bueno en estanterías densas)."""
    try:
        r = get_yolo().predict(imagen, imgsz=960, conf=settings.YOLO_CONFIDENCE,
                               max_det=1000, verbose=False)[0]
    except MLUnavailable:
        return []
    return r.boxes.xyxy.cpu().numpy().astype(int).tolist()


def _area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def _inter(a, b):
    return _area([max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])])


def _solapa(a, b, umbral=0.5):
    """True si una caja está (casi) dentro de la otra o se parecen mucho."""
    i = _inter(a, b)
    menor = min(_area(a), _area(b)) or 1
    return i / menor > umbral


def detect(imagen):
    """Cajas candidatas (OWLv2 + YOLO) y, aparte, las de YOLO."""
    ancho, alto = imagen.size
    total = ancho * alto
    cajas = []
    try:
        cajas += propose_objects(imagen)[0]
    except MLUnavailable:
        pass
    yolo = [c for c in _yolo_boxes(imagen) if _area(c) / total >= MIN_AREA]
    cajas = [c for c in cajas if _area(c) / total >= MIN_AREA] + yolo
    return cajas, yolo


# ---------- Reconocimiento ----------

def identify(imagen, cajas):
    """Decide qué producto es cada caja. Devuelve [(caja, product_id, puntaje), ...].

    Solo se aceptan coincidencias claras (similitud alta y ventaja sobre el segundo producto);
    de las cajas que se pisan gana la de mayor similitud, así un objeto cuenta una sola vez.
    """
    matriz, duenos = _referencias()
    if matriz is None or not len(cajas):
        return []

    try:
        candidatas = list(cajas[:MAX_CROPS])
        embs = embed_images([imagen.crop(c) for c in candidatas])
    except MLUnavailable:
        return []

    productos = sorted(set(duenos.tolist()))
    sim = embs @ matriz.T
    por_producto = np.stack(
        [sim[:, duenos == p].max(axis=1) for p in productos], axis=1)  # (cajas, productos)

    ancho, alto = imagen.size
    propuestas = []
    for i, caja in enumerate(candidatas):
        orden = np.argsort(por_producto[i])[::-1]
        mejor = por_producto[i, orden[0]]
        segundo = por_producto[i, orden[1]] if len(orden) > 1 else -1.0
        if mejor >= settings.CLIP_MATCH_THRESHOLD and (mejor - segundo) >= settings.CLIP_MATCH_MARGIN:
            propuestas.append((float(mejor), caja, productos[orden[0]]))

    aceptadas = []
    for puntaje, caja, pid in sorted(propuestas, key=lambda x: -x[0]):
        if all(not _solapa(caja, a[0], 0.35 if a[1] == pid else 0.5) for a in aceptadas):
            aceptadas.append((caja, pid, puntaje))

    if not aceptadas:
        # Foto de un solo producto (sin cajas útiles): se prueba con la imagen completa
        v = embed_images([imagen])[0]
        s = np.array([(matriz[duenos == p] @ v).max() for p in productos])
        orden = np.argsort(s)[::-1]
        segundo = s[orden[1]] if len(s) > 1 else -1.0
        if s[orden[0]] >= settings.CLIP_MATCH_THRESHOLD and s[orden[0]] - segundo >= settings.CLIP_MATCH_MARGIN:
            aceptadas.append(([0, 0, ancho, alto], productos[orden[0]], float(s[orden[0]])))
    return aceptadas


# ---------- Resultado ----------

def _fuente(tam):
    try:
        return ImageFont.load_default(size=tam)
    except TypeError:  # Pillow antiguo
        return ImageFont.load_default()


def _dibujar(imagen, reconocidas, sin_identificar, nombres):
    anotada = imagen.copy()
    draw = ImageDraw.Draw(anotada)
    grosor = max(2, imagen.width // 350)
    fuente = _fuente(max(12, imagen.width // 45))
    for caja in sin_identificar:
        draw.rectangle(caja, outline='#ff9f0a', width=grosor)
    for caja, pid, puntaje in reconocidas:
        draw.rectangle(caja, outline='#0071e3', width=grosor + 1)
        etiqueta = f'{nombres.get(pid, "")[:18]} {puntaje:.0%}'
        x, y = caja[0], max(0, caja[1] - fuente.size - 6) if hasattr(fuente, 'size') else caja[1]
        ancho_txt = draw.textlength(etiqueta, font=fuente)
        draw.rectangle([x, y, x + ancho_txt + 8, y + getattr(fuente, 'size', 12) + 6], fill='#0071e3')
        draw.text((x + 4, y + 2), etiqueta, fill='white', font=fuente)
    buffer = io.BytesIO()
    anotada.save(buffer, format='JPEG', quality=88)
    return buffer.getvalue()


@transaction.atomic
def analyze(uploaded_file, user=None, notes=''):
    """Ejecuta el análisis completo y guarda la inspección con sus resultados."""
    imagen = ImageOps.exif_transpose(Image.open(uploaded_file)).convert('RGB')
    imagen.thumbnail((MAX_SIDE, MAX_SIDE))

    cajas, yolo = detect(imagen)
    reconocidas = identify(imagen, cajas)

    # Cajas de YOLO sin producto asociado = objetos que el sistema no pudo identificar
    sin_identificar = []
    for caja in yolo:
        if all(not _solapa(caja, r[0]) for r in reconocidas) and \
                all(not _solapa(caja, s, 0.8) for s in sin_identificar):
            sin_identificar.append(caja)

    conteo = Counter(pid for _, pid, _ in reconocidas)
    productos = Product.objects.in_bulk(list(conteo))
    nombres = {pid: p.name for pid, p in productos.items()}

    original = io.BytesIO()
    imagen.save(original, format='JPEG', quality=90)

    inspection = Inspection(
        total_detected=len(reconocidas) + len(sin_identificar),
        unidentified=len(sin_identificar), notes=notes, created_by=user)
    inspection.image.save('analisis.jpg', ContentFile(original.getvalue()), save=False)
    inspection.annotated_image.save(
        'analizada.jpg',
        ContentFile(_dibujar(imagen, reconocidas, sin_identificar, nombres)), save=False)
    inspection.save()

    for pid, detectadas in conteo.items():
        producto = productos[pid]
        InspectionItem.objects.create(
            inspection=inspection, product=producto,
            detected=detectadas, expected=producto.stock)
        if detectadas != producto.stock:
            _alerta_diferencia(producto, detectadas, inspection)
    return inspection


def _alerta_diferencia(producto, detectadas, inspection):
    mensaje = (f'Análisis #{inspection.pk}: se detectaron {detectadas} unidades de '
               f'«{producto.name}» y el sistema registra {producto.stock}.')
    Alert.objects.create(product=producto, kind=Alert.MISMATCH, message=mensaje)


@transaction.atomic
def apply_to_inventory(inspection, user):
    """Ajusta el stock de cada producto identificado al conteo detectado."""
    for item in inspection.items.select_related('product'):
        if item.detected != item.product.stock:
            apply_movement(
                item.product_id, StockMovement.ADJUST, item.detected, user=user,
                description=f'Ajuste por análisis visual #{inspection.pk}')
        Alert.objects.filter(
            product=item.product, kind=Alert.MISMATCH, is_resolved=False
        ).update(is_resolved=True)
    inspection.applied = True
    inspection.save(update_fields=['applied'])
