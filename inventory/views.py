from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import StockMovementForm
from .models import Alert, StockMovement
from .services import StockError, apply_movement


@login_required
@permission_required('inventory.view_stockmovement', raise_exception=True)
def movement_list(request):
    movements = StockMovement.objects.select_related('product', 'created_by')[:300]
    return render(request, 'inventario/movement_list.html', {'movements': movements})


@login_required
@permission_required('inventory.add_stockmovement', raise_exception=True)
def movement_create(request):
    if request.method == 'POST':
        form = StockMovementForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                apply_movement(
                    data['product'].pk, data['movement_type'], data['quantity'],
                    user=request.user, description=data['description'])
            except StockError as e:
                form.add_error('quantity', str(e))
            else:
                messages.success(request, 'Movimiento registrado correctamente.')
                return redirect('movement_list')
    else:
        initial = {}
        if request.GET.get('product'):
            initial['product'] = request.GET['product']
        form = StockMovementForm(initial=initial)

    return render(request, 'inventario/movement_form.html', {'form': form})


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
