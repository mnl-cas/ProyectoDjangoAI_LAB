"""Lógica de inventario: aplicar movimientos y mantener las alertas al día."""
from django.db import transaction
from django.utils import timezone

from catalog.models import Product

from .models import Alert, StockMovement


class StockError(Exception):
    """Movimiento inválido (por ejemplo, sacar más de lo que hay)."""


@transaction.atomic
def apply_movement(product_id, movement_type, quantity, user=None, description=''):
    """Registra un movimiento y actualiza el stock del producto de forma atómica."""
    product = Product.objects.select_for_update().get(pk=product_id)

    if movement_type == StockMovement.IN:
        product.stock += quantity
    elif movement_type == StockMovement.OUT:
        if quantity > product.stock:
            raise StockError(
                f'No hay suficiente stock de «{product.name}»: '
                f'disponible {product.stock}, solicitado {quantity}.')
        product.stock -= quantity
    elif movement_type == StockMovement.ADJUST:
        product.stock = quantity
    else:
        raise StockError('Tipo de movimiento no válido.')

    product.save()  # dispara refresh_stock_alerts mediante la señal post_save
    return StockMovement.objects.create(
        product=product, movement_type=movement_type, quantity=quantity,
        description=description, created_by=user)


def refresh_stock_alerts(product):
    """Crea o resuelve las alertas de stock bajo / agotado según el stock actual."""
    stock_kinds = [Alert.LOW_STOCK, Alert.OUT_OF_STOCK]
    abiertas = Alert.objects.filter(product=product, is_resolved=False, kind__in=stock_kinds)

    if product.stock == 0:
        kind = Alert.OUT_OF_STOCK
        msg = f'«{product.name}» está agotado.'
    elif product.stock <= product.min_stock:
        kind = Alert.LOW_STOCK
        msg = (f'«{product.name}» tiene stock bajo: {product.stock} '
               f'unidades (mínimo {product.min_stock}).')
    else:
        abiertas.update(is_resolved=True, resolved_at=timezone.now())
        return None

    abiertas.exclude(kind=kind).update(is_resolved=True, resolved_at=timezone.now())
    alerta = abiertas.filter(kind=kind).first()
    if alerta:
        if alerta.message != msg:
            alerta.message = msg
            alerta.save(update_fields=['message'])
        return alerta
    return Alert.objects.create(product=product, kind=kind, message=msg)
