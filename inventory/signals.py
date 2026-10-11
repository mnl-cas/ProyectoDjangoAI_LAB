from django.db.models.signals import post_save
from django.dispatch import receiver

from catalog.models import Product

from .services import refresh_stock_alerts


@receiver(post_save, sender=Product)
def producto_guardado(sender, instance, **kwargs):
    refresh_stock_alerts(instance)
