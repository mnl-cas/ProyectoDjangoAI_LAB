from django.contrib.auth.decorators import user_passes_test


def user_in_roles(user, roles):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name__in=roles).exists())


def es_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


# Decorador para las vistas de administración de usuarios, grupos y permisos
solo_admin = user_passes_test(es_admin, login_url='login')
