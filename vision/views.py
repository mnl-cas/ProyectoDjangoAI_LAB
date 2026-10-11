from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .ml import MLUnavailable
from .models import Inspection


@login_required
@permission_required('vision.add_inspection', raise_exception=True)
def inspection_create(request):
    if request.method == 'POST':
        archivo = request.FILES.get('image')
        if not archivo:
            messages.error(request, 'Selecciona una foto para analizar.')
            return redirect('inspection_create')
        try:
            inspection = services.analyze(
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
        services.apply_to_inventory(inspection, request.user)
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
