"""Demo del modelo desde Python (sin navegador).

Uso (desde la raíz del proyecto):
  python -m visionstock_project.ia.demo FOTO_ESTANTERIA                      # solo YOLO: cuenta objetos
  python -m visionstock_project.ia.demo FOTO_ESTANTERIA -p "Coca-Cola" REF1.jpg REF2.jpg
      # YOLO + OWLv2 + DINOv2: cuenta cuántas unidades del producto hay, con las fotos de referencia
"""
import argparse
import os
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visionstock_project.settings')
django.setup()

import numpy as np  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

from visionstock_project.ia import buscador  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('foto')
    ap.add_argument('-p', '--producto', help='nombre del producto a contar')
    ap.add_argument('refs', nargs='*', help='fotos de referencia del producto')
    args = ap.parse_args()

    imagen = ImageOps.exif_transpose(Image.open(args.foto)).convert('RGB')
    imagen.thumbnail((buscador.CONFIG['max_lado'], buscador.CONFIG['max_lado']))
    print(f'Foto: {args.foto} {imagen.size}')

    cajas, yolo = buscador.detectar(imagen)
    print(f'YOLO11 (SKU-110K) detectó {len(yolo)} objetos; con OWLv2 hay {len(cajas)} cajas candidatas.')

    if not args.producto or not args.refs:
        return

    vectores = np.vstack([buscador.vectores_referencia(ImageOps.exif_transpose(Image.open(r)).convert('RGB'))
                          for r in args.refs])
    print(f'{len(args.refs)} fotos de referencia -> {len(vectores)} vectores DINOv2')

    # Un solo producto (id 1): no hay "segundo producto" con el que comparar
    reconocidas = buscador.identificar(imagen, cajas, vectores.astype('float32'), np.array([1] * len(vectores)))
    print(f'DINOv2 reconoció {len(reconocidas)} unidades de «{args.producto}»')
    for caja, _, puntaje in reconocidas:
        print(f'  caja={caja} similitud={puntaje:.0%}')


if __name__ == '__main__':
    sys.exit(main())
