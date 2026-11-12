import io
from collections import Counter

import numpy as np
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from PIL import Image, ImageOps

from catalog.models import Product, ReferenceImage
from inventory.models import Alert, StockMovement, apply_movement
from visionstock_project.ia.buscador import (
    CONFIG, MLUnavailable, detectar, dibujar, identificar, se_solapan, tamano_vector)

from .models import Inspection, InspectionItem


def referencias():  # Lee de la base de datos los vectores de todas las referencias.
    vectores, duenos = [], []  # Vectores y producto al que pertenece cada uno.
    tamano = tamano_vector()  # Tamaño de vector del modelo actual.
    for ref in ReferenceImage.objects.exclude(embedding__isnull=True):  # Recorre las referencias con vector.
        for v in ref.embedding or []:  # Cada referencia guarda una lista de vectores.
            if len(v) == tamano:  # Ignora vectores viejos de otro modelo (hay que recalcularlos).
                vectores.append(v)
                duenos.append(ref.product_id)
    if not vectores:  # Si no hay ninguno, no se puede reconocer nada.
        return None, np.array([])
    return np.asarray(vectores, dtype='float32'), np.asarray(duenos)


@transaction.atomic
def analyze(uploaded_file, user=None, notes=''):
    """Ejecuta el análisis completo y guarda la inspección con sus resultados."""
    imagen = ImageOps.exif_transpose(Image.open(uploaded_file)).convert('RGB')
    imagen.thumbnail((CONFIG['max_lado'], CONFIG['max_lado']))

    cajas, yolo = detectar(imagen)  # Cajas candidatas.
    matriz, duenos = referencias()  # Vectores de las fotos de referencia.
    reconocidas = identificar(imagen, cajas, matriz, duenos)  # Qué producto es cada caja.

    # Cajas de YOLO sin producto asociado = objetos que el sistema no pudo identificar
    sin_identificar = []
    for caja in yolo:
        if all(not se_solapan(caja, r[0]) for r in reconocidas) and \
                all(not se_solapan(caja, s, 0.8) for s in sin_identificar):
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
        ContentFile(dibujar(imagen, reconocidas, sin_identificar, nombres)), save=False)
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


@login_required
@permission_required('vision.add_inspection', raise_exception=True)
def inspection_create(request):
    if request.method == 'POST':
        archivo = request.FILES.get('image')
        if not archivo:
            messages.error(request, 'Selecciona una foto para analizar.')
            return redirect('inspection_create')
        try:
                    inspection = analyze(
                archivo, user=request.user, notes=request.POST.get('notes', '').strip())
        except MLUnavailable as e:
            messages.error(request, str(e))
            return redirect('inspection_create')
        except OSError:
            messages.error(request, 'El archivo no es una imagen válida.')
            return redirect('inspection_create')
        messages.success(
            request, f'Análisis completado: {inspection.total_detected} unidades detectadas.')
        return redirect('inspection_detail', pk=inspection.pk)
    return render(request, 'vision/inspection_form.html')


@login_required
@permission_required('vision.view_inspection', raise_exception=True)
def inspection_list(request):
    inspections = Inspection.objects.select_related('created_by')[:200]
    return render(request, 'vision/inspection_list.html', {'inspections': inspections})


@login_required
@permission_required('vision.view_inspection', raise_exception=True)
def inspection_detail(request, pk):
    inspection = get_object_or_404(Inspection.objects.select_related('created_by'), pk=pk)
    return render(request, 'vision/inspection_detail.html', {
        'inspection': inspection,
        'items': inspection.items.select_related('product'),
    })


@login_required
@permission_required('vision.change_inspection', raise_exception=True)
@permission_required('inventory.add_stockmovement', raise_exception=True)
@require_POST
def inspection_apply(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk)
    if inspection.applied:
        messages.warning(request, 'Este análisis ya se aplicó al inventario.')
    else:
        apply_to_inventory(inspection, request.user)
        messages.success(request, 'El inventario se ajustó con los conteos detectados.')
    return redirect('inspection_detail', pk=pk)


@login_required
@permission_required('vision.delete_inspection', raise_exception=True)
@require_POST
def inspection_delete(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk)
    inspection.image.delete(save=False)
    inspection.annotated_image.delete(save=False)
    inspection.delete()
    messages.success(request, 'Análisis eliminado.')
    return redirect('inspection_list')
