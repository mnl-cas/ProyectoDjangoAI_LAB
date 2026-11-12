"""Servicio de visión: detecta objetos en una estantería y reconoce qué producto es cada uno."""  # Describe qué hace este módulo.

from __future__ import annotations  # Permite anotar tipos con strings en versiones anteriores de Python.

import io  # Para guardar la imagen anotada en memoria.
import json  # Proporciona utilidades para leer el archivo de configuración.
import os  # Facilita construir rutas de archivos.

import numpy as np  # Maneja los vectores (embeddings) como arreglos.
import torch  # Motor de los modelos de Hugging Face.
from django.conf import settings  # Da acceso a BASE_DIR.
from PIL import ImageDraw, ImageFont  # Dibuja las cajas sobre la foto.
from torchvision.ops import nms  # Elimina cajas repetidas.

ARTEFACTS_DIR = os.path.join(settings.BASE_DIR, "visionstock_project", "ia", "artefactos")  # Carpeta donde viven los artefactos.

with open(os.path.join(ARTEFACTS_DIR, "config.json"), encoding="utf-8") as cfg_file:  # Abre la configuración de los modelos.
    CONFIG = json.load(cfg_file)  # Carga los parámetros (modelos, umbrales) en memoria.

YOLO = None  # YOLO se carga la primera vez que se usa.
DINO = None  # DINOv2 (procesador y modelo) se carga la primera vez que se usa.
OWL = None  # OWLv2 (procesador y modelo) se carga la primera vez que se usa.


class MLUnavailable(Exception):  # Error propio cuando un modelo no se puede cargar.
    """No se pudo cargar un modelo (falta la librería, el archivo o la descarga)."""


# ---------- Carga de modelos ----------

def cargar_yolo():  # YOLO11 entrenado en SKU-110K (muy bueno en estanterías densas).
    global YOLO  # Usamos la variable del módulo.
    if YOLO is None:  # Si todavía no se ha cargado...
        ruta = os.path.join(ARTEFACTS_DIR, CONFIG["yolo_archivo"])  # Ruta del archivo .pt.
        if not os.path.isfile(ruta):  # Verifica que el archivo exista.
            raise MLUnavailable(f"No se encontró el modelo YOLO en {ruta}.")
        try:  # Intenta cargar el modelo.
            from ultralytics import YOLO as Yolo  # Librería que trae YOLO.
            YOLO = Yolo(ruta)  # Carga los pesos entrenados.
        except Exception as e:  # Si algo falla, avisa con un error propio.
            raise MLUnavailable(f"No se pudo cargar YOLO: {e}") from e
    return YOLO


def cargar_dino():  # DINOv2 convierte imágenes en vectores (embeddings).
    global DINO  # Usamos la variable del módulo.
    if DINO is None:  # Si todavía no se ha cargado...
        try:  # Intenta descargarlo/cargarlo desde Hugging Face.
            from transformers import AutoImageProcessor, AutoModel
            nombre = CONFIG["embedding_modelo"]
            DINO = (AutoImageProcessor.from_pretrained(nombre), AutoModel.from_pretrained(nombre).eval())
        except Exception as e:
            raise MLUnavailable(f"No se pudo cargar DINOv2: {e}") from e
    return DINO  # Devuelve (procesador, modelo).


def cargar_owl():  # OWLv2 propone cajas de cualquier objeto.
    global OWL  # Usamos la variable del módulo.
    if OWL is None:  # Si todavía no se ha cargado...
        try:  # Intenta descargarlo/cargarlo desde Hugging Face.
            from transformers import Owlv2ForObjectDetection, Owlv2Processor
            nombre = CONFIG["owl_modelo"]
            OWL = (Owlv2Processor.from_pretrained(nombre), Owlv2ForObjectDetection.from_pretrained(nombre).eval())
        except Exception as e:
            raise MLUnavailable(f"No se pudo cargar OWLv2: {e}") from e
    return OWL  # Devuelve (procesador, modelo).


# ---------- Cajas ----------

def proponer_objetos(imagen, min_objectness=0.2, iou=0.3):  # Cajas de cualquier objeto que haya en la imagen.
    procesador, modelo = cargar_owl()  # Obtiene OWLv2.
    ancho, alto = imagen.size  # Tamaño de la foto.
    lado = max(ancho, alto)  # OWLv2 rellena la imagen hasta hacerla cuadrada.
    with torch.no_grad():  # No se entrena, solo se predice.
        salida = modelo(**procesador(text=[["a product"]], images=imagen, return_tensors="pt"))
    objeto = salida.objectness_logits.sigmoid()[0]  # Qué tan "objeto" parece cada caja (0 a 1).
    cx, cy, w, h = salida.pred_boxes[0].unbind(-1)  # Las cajas vienen como centro, ancho y alto.
    cajas = torch.stack([(cx - w / 2) * lado, (cy - h / 2) * lado,
                         (cx + w / 2) * lado, (cy + h / 2) * lado], dim=-1)  # Pasa a esquinas x1, y1, x2, y2.
    cajas[:, 0::2] = cajas[:, 0::2].clamp(0, ancho)  # Evita que las cajas se salgan de la foto (x).
    cajas[:, 1::2] = cajas[:, 1::2].clamp(0, alto)  # Evita que las cajas se salgan de la foto (y).
    ok = objeto > min_objectness  # Descarta las cajas que no parecen un objeto.
    cajas, objeto = cajas[ok], objeto[ok]  # Se queda solo con las buenas.
    keep = nms(cajas, objeto, iou)  # Elimina las cajas que se repiten.
    return cajas[keep].round().int().tolist(), objeto[keep].tolist()  # Devuelve cajas y puntajes.


def cajas_yolo(imagen):  # Cajas de YOLO11 (x1, y1, x2, y2).
    try:
        r = cargar_yolo().predict(imagen, imgsz=960, conf=CONFIG["yolo_confianza"],
                                  max_det=1000, verbose=False)[0]
    except MLUnavailable:  # Si YOLO no está, se sigue sin él.
        return []
    return r.boxes.xyxy.cpu().numpy().astype(int).tolist()


def area(b):  # Área de una caja.
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def interseccion(a, b):  # Área donde dos cajas se cruzan.
    return area([max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])])


def se_solapan(a, b, umbral=0.5):  # True si una caja está (casi) dentro de la otra.
    menor = min(area(a), area(b)) or 1
    return interseccion(a, b) / menor > umbral


def es_fondo(imagen, caja):  # True si la caja es casi de un solo color (pared o estante vacío).
    gris = np.asarray(imagen.crop(caja).convert("L"), dtype="float32")  # Recorte en escala de grises.
    if gris.size == 0:  # Una caja sin área no sirve.
        return True
    parecidos = np.abs(gris - np.median(gris)) < 25  # Píxeles con casi el mismo tono que el central.
    return parecidos.mean() > 0.88  # Si casi todos son iguales, no hay ningún producto.


def detectar(imagen):  # Cajas candidatas (OWLv2 + YOLO) y, aparte, las de YOLO.
    ancho, alto = imagen.size
    total = ancho * alto  # Área de la foto.
    cajas = []
    try:
        cajas += proponer_objetos(imagen)[0]  # Cajas de OWLv2.
    except MLUnavailable:
        pass
    yolo = [c for c in cajas_yolo(imagen) if area(c) / total >= CONFIG["area_minima"]]  # Cajas de YOLO.
    cajas = [c for c in cajas if area(c) / total >= CONFIG["area_minima"]] + yolo  # Se juntan, sin cajas diminutas.
    yolo = [c for c in yolo if not es_fondo(imagen, c)]  # Fuera las cajas que solo ven pared o estante vacío.
    cajas = [c for c in cajas if not es_fondo(imagen, c)]
    return cajas, yolo


# ---------- Vectores ----------

def vectores_imagenes(imagenes):  # Convierte una lista de imágenes PIL en vectores normalizados.
    if not imagenes:  # Si no hay imágenes, no hay nada que calcular.
        return np.zeros((0, 0), dtype="float32")
    procesador, modelo = cargar_dino()  # Obtiene DINOv2.
    with torch.no_grad():  # No se entrena, solo se predice.
        salida = modelo(**procesador(images=[i.convert("RGB") for i in imagenes], return_tensors="pt"))
    vectores = salida.last_hidden_state[:, 0]  # El primer token resume toda la imagen.
    vectores = torch.nn.functional.normalize(vectores, dim=-1)  # Normaliza: producto punto = similitud coseno.
    return vectores.numpy().astype("float32")  # Devuelve un arreglo (n, 384).


def vectores_referencia(imagen):  # Vector de una foto de referencia (solo el producto, sin el fondo).
    producto = imagen  # Si no se encuentra el objeto, se usa la foto completa.
    try:  # OWLv2 busca el objeto principal.
        cajas, puntajes = proponer_objetos(imagen)
        ancho, alto = imagen.size
        candidatas = [(p, c) for c, p in zip(cajas, puntajes)
                      if 0.03 < area(c) / (ancho * alto) < 0.85]  # Ni muy pequeña ni toda la foto.
        if candidatas:  # Si hay candidatas...
            producto = imagen.crop(max(candidatas)[1])  # ...se recorta la de mayor puntaje.
    except MLUnavailable:  # Sin OWLv2 se usa la foto completa.
        pass
    return vectores_imagenes([producto]).tolist()  # Lista con un vector de 384 números.


def tamano_vector():  # Tamaño de los vectores del modelo actual.
    return cargar_dino()[1].config.hidden_size


# ---------- Reconocimiento ----------

def puntaje_producto(sim, duenos, productos):  # Similitud de cada caja con cada producto.
    columnas = []  # Una columna por producto.
    for p in productos:  # Para cada producto...
        columnas.append(sim[:, duenos == p].max(axis=1))  # ...se toma su foto de referencia más parecida.
    return np.stack(columnas, axis=1)  # Matriz (cajas, productos).


def es_claro(puntajes):  # True si el mejor producto supera el umbral y le gana al segundo.
    orden = np.argsort(puntajes)[::-1]  # Índices de mayor a menor similitud.
    mejor = puntajes[orden[0]]
    segundo = puntajes[orden[1]] if len(orden) > 1 else -1.0
    return mejor >= CONFIG["umbral_similitud"] and (mejor - segundo) >= CONFIG["margen_similitud"]


def identificar(imagen, cajas, matriz, duenos):  # Decide qué producto es cada caja: [(caja, product_id, puntaje), ...].
    if matriz is None or not len(cajas):  # Sin referencias o sin cajas no hay nada que hacer.
        return []

    try:
        candidatas = list(cajas[:CONFIG["max_recortes"]])  # Se limita la cantidad de recortes.
        embs = vectores_imagenes([imagen.crop(c) for c in candidatas])  # Un vector por recorte.
    except MLUnavailable:
        return []

    productos = sorted(set(duenos.tolist()))  # Ids de los productos con referencias.
    por_producto = puntaje_producto(embs @ matriz.T, duenos, productos)  # Similitud (cajas, productos).

    propuestas = []  # Cajas que parecen un producto.
    for i, caja in enumerate(candidatas):
        if es_claro(por_producto[i]):  # Solo coincidencias claras.
            mejor = int(np.argmax(por_producto[i]))
            propuestas.append((float(por_producto[i, mejor]), caja, productos[mejor]))

    aceptadas = []  # Gana la caja de mayor similitud entre las que se pisan.
    for puntaje, caja, pid in sorted(propuestas, key=lambda x: -x[0]):
        if all(not se_solapan(caja, a[0], 0.35 if a[1] == pid else 0.5) for a in aceptadas):
            aceptadas.append((caja, pid, puntaje))

    if not aceptadas:  # Foto de un solo producto: se prueba con la imagen completa.
        v = vectores_imagenes([imagen])[0]
        s = puntaje_producto((matriz @ v)[None, :], duenos, productos)[0]
        if es_claro(s):
            ancho, alto = imagen.size
            aceptadas.append(([0, 0, ancho, alto], productos[int(np.argmax(s))], float(s.max())))
    return aceptadas


# ---------- Dibujo ----------

def fuente(tam):  # Fuente para las etiquetas.
    try:
        return ImageFont.load_default(size=tam)
    except TypeError:  # Pillow antiguo
        return ImageFont.load_default()


def dibujar(imagen, reconocidas, sin_identificar, nombres):  # Devuelve la foto con las cajas dibujadas (JPEG en bytes).
    anotada = imagen.copy()  # No se modifica la original.
    draw = ImageDraw.Draw(anotada)
    grosor = max(2, imagen.width // 350)  # Grosor de las líneas según el tamaño de la foto.
    letra = fuente(max(12, imagen.width // 45))
    for caja in sin_identificar:  # Naranja: objetos que no se pudieron identificar.
        draw.rectangle(caja, outline="#ff9f0a", width=grosor)
    for caja, pid, puntaje in reconocidas:  # Azul: productos reconocidos, con nombre y porcentaje.
        draw.rectangle(caja, outline="#0071e3", width=grosor + 1)
        etiqueta = f'{nombres.get(pid, "")[:18]} {puntaje:.0%}'
        x, y = caja[0], max(0, caja[1] - getattr(letra, "size", 12) - 6)
        ancho_txt = draw.textlength(etiqueta, font=letra)
        draw.rectangle([x, y, x + ancho_txt + 8, y + getattr(letra, "size", 12) + 6], fill="#0071e3")
        draw.text((x + 4, y + 2), etiqueta, fill="white", font=letra)
    buffer = io.BytesIO()
    anotada.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()
