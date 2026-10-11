from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import render

from catalog.models import Category, Product
from inventory.models import Alert, StockMovement
from vision.models import Inspection


@login_required
def home(request):
    productos = Product.objects.all()
    bajos = productos.filter(stock__lte=F('min_stock')).order_by('stock')[:6]
    return render(request, 'dashboard/home.html', {
        'total_productos': productos.count(),
        'total_categorias': Category.objects.count(),
        'unidades': sum(productos.values_list('stock', flat=True)),
        'alertas_abiertas': Alert.objects.filter(is_resolved=False).count(),
        'bajos': bajos,
        'movimientos': StockMovement.objects.select_related('product')[:6],
        'analisis': Inspection.objects.count(),
        'ultimos_analisis': Inspection.objects.all()[:4],
    })
