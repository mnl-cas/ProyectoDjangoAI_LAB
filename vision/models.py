from django.conf import settings
from django.db import models

from catalog.models import Product


class Inspection(models.Model):
    """Un análisis de una foto de estantería con el modelo YOLO."""

    image = models.ImageField(upload_to='inspections/', verbose_name='Foto original')
    annotated_image = models.ImageField(
        upload_to='inspections/annotated/', blank=True, verbose_name='Foto analizada')
    total_detected = models.PositiveIntegerField(default=0, verbose_name='Unidades detectadas')
    unidentified = models.PositiveIntegerField(default=0, verbose_name='Sin identificar')
    notes = models.CharField(max_length=255, blank=True, verbose_name='Observaciones')
    applied = models.BooleanField(default=False, verbose_name='Aplicado al inventario')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        blank=True, related_name='inspections', verbose_name='Analizado por')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')

    class Meta:
        verbose_name = 'Análisis'
        verbose_name_plural = 'Análisis'
        ordering = ['-created_at']

    def __str__(self):
        return f'Análisis #{self.pk} · {self.total_detected} unidades'


class InspectionItem(models.Model):
    """Cantidad detectada de un producto concreto dentro de un análisis."""

    inspection = models.ForeignKey(
        Inspection, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='inspection_items')
    detected = models.PositiveIntegerField(verbose_name='Detectadas')
    expected = models.PositiveIntegerField(verbose_name='Stock en sistema')

    class Meta:
        verbose_name = 'Producto detectado'
        verbose_name_plural = 'Productos detectados'
        ordering = ['product__name']

    @property
    def difference(self):
        return self.detected - self.expected

    def __str__(self):
        return f'{self.product.name}: {self.detected}'
