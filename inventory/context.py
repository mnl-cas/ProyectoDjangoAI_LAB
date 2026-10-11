def alertas(request):
    """Número de alertas abiertas para el contador de la barra de navegación."""
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated or not user.has_perm('inventory.view_alert'):
        return {}
    from .models import Alert
    return {'alertas_abiertas': Alert.objects.filter(is_resolved=False).count()}
