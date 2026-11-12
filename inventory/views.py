from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalog.models import Product

from .models import Alert, StockMovement, StockError, apply_movement



@login_required
@permission_required('inventory.view_stockmovement', raise_exception=True)
def movement_list(request):
    movements = StockMovement.objects.select_related('product', 'created_by')[:300]
    return render(request, 'inventario/movement_list.html', {'movements': movements})


@login_required
@permission_required('inventory.add_stockmovement', raise_exception=True)
def movement_create(request):
    valores = {'product': request.GET.get('product', ''), 'movement_type': 'IN', 'quantity': '', 'description': ''}
    if request.method == 'POST':
        valores = {
            'product': request.POST.get('product', ''),
            'movement_type': request.POST.get('movement_type', ''),
            'quantity': request.POST.get('quantity', '').strip(),
            'description': request.POST.get('description', '').strip(),
        }
        tipos = [t[0] for t in StockMovement.MOVEMENT_TYPES]
        if not Product.objects.filter(pk=valores['product'] or 0).exists():
            messages.error(request, 'Selecciona un producto.')
        elif valores['movement_type'] not in tipos:
            messages.error(request, 'Selecciona el tipo de movimiento.')
        elif not valores['quantity'].isdigit():
            messages.error(request, 'La cantidad debe ser un número entero.')
        else:
            try:
                apply_movement(
                    int(valores['product']), valores['movement_type'], int(valores['quantity']),
                    user=request.user, description=valores['description'])
            except StockError as e:
                messages.error(request, str(e))
            else:
                messages.success(request, 'Movimiento registrado correctamente.')
                return redirect('movement_list')

    return render(request, 'inventario/movement_form.html', {
        'valores': valores, 'products': Product.objects.all(),
        'tipos': StockMovement.MOVEMENT_TYPES})


@login_required
@permission_required('inventory.view_alert', raise_exception=True)
def alert_list(request):
    mostrar = request.GET.get('ver', 'abiertas')
    alertas = Alert.objects.select_related('product')
    if mostrar == 'abiertas':
        alertas = alertas.filter(is_resolved=False)
    elif mostrar == 'resueltas':
        alertas = alertas.filter(is_resolved=True)
    return render(request, 'inventario/alert_list.html', {
        'alertas': alertas[:300],
        'ver': mostrar,
        'abiertas': Alert.objects.filter(is_resolved=False).count(),
    })


@login_required
@permission_required('inventory.change_alert', raise_exception=True)
@require_POST
def alert_resolve(request, pk):
    alerta = get_object_or_404(Alert, pk=pk)
    alerta.is_resolved = True
    alerta.resolved_at = timezone.now()
    alerta.save(update_fields=['is_resolved', 'resolved_at'])
    messages.success(request, 'Alerta marcada como resuelta.')
    return redirect('alert_list')

def alertas(request):
    """Context processor: número de alertas abiertas para la barra de navegación."""
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated or not user.has_perm('inventory.view_alert'):
        return {}
    return {'alertas_abiertas': Alert.objects.filter(is_resolved=False).count()}
