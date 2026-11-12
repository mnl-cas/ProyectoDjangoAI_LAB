from django.conf import settings
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from catalog.models import Product

class StockMovement(models.Model):
    IN = 'IN'
    OUT = 'OUT'
    ADJUST = 'ADJUST'
    MOVEMENT_TYPES = [
        (IN, 'Entrada'),
        (OUT, 'Salida'),
        (ADJUST, 'Ajuste (fija el stock)'),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='movements',
        verbose_name='Producto',
    )
    movement_type = models.CharField(
        max_length=6, choices=MOVEMENT_TYPES, verbose_name='Tipo de movimiento'
    )
    quantity = models.PositiveIntegerField(verbose_name='Cantidad')
    description = models.CharField(
        max_length=255, blank=True, verbose_name='Motivo / Observaciones'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        blank=True, related_name='stock_movements', verbose_name='Registrado por',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')

    class Meta:
        verbose_name = 'Movimiento de inventario'
        verbose_name_plural = 'Movimientos de inventario'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_movement_type_display()} {self.quantity} · {self.product.name}'


class Alert(models.Model):
    LOW_STOCK = 'LOW_STOCK'
    OUT_OF_STOCK = 'OUT_OF_STOCK'
    MISMATCH = 'MISMATCH'
    KINDS = [
        (LOW_STOCK, 'Stock bajo'),
        (OUT_OF_STOCK, 'Agotado'),
        (MISMATCH, 'Diferencia detectada'),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='alerts',
        verbose_name='Producto',
    )
    kind = models.CharField(max_length=14, choices=KINDS, verbose_name='Tipo')
    message = models.CharField(max_length=255, verbose_name='Mensaje')
    is_resolved = models.BooleanField(default=False, verbose_name='Resuelta')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['is_resolved', '-created_at']

    def __str__(self):
        return f'{self.get_kind_display()} · {self.product.name}'
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

@receiver(post_save, sender=Product)
def producto_guardado(sender, instance, **kwargs):
    refresh_stock_alerts(instance)
