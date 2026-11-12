"""Rutas principales de VisionStock."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),           # login/, registro/, usuarios/, grupos/, permisos/
    path('', include('catalog.urls')),            # Inicio, productos y categorías
    path('inventario/', include('inventory.urls')),  # Movimientos y alertas
    path('analisis/', include('vision.urls')),    # Análisis con visión artificial
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
