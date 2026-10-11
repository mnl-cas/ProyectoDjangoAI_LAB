from django.conf import settings
from django.db import models

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
