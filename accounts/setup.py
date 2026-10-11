"""Datos iniciales de acceso: grupos con permisos y usuario administrador."""
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User

GRUPO_ADMIN = 'Administrador'
GRUPO_OPERADOR = 'Operador'
GRUPO_CONSULTA = 'Consulta'

# Permisos por grupo: {app: {modelo: [acciones]}}
PERMISOS_OPERADOR = {
    'catalog': {'category': ['view', 'add', 'change'], 'product': ['view', 'add', 'change'],
                'referenceimage': ['view', 'add', 'delete']},
    'inventory': {'stockmovement': ['view', 'add'], 'alert': ['view', 'change']},
    'vision': {'inspection': ['view', 'add', 'change'], 'inspectionitem': ['view']},
}
PERMISOS_CONSULTA = {
    'catalog': {'category': ['view'], 'product': ['view'], 'referenceimage': ['view']},
    'inventory': {'stockmovement': ['view'], 'alert': ['view']},
    'vision': {'inspection': ['view'], 'inspectionitem': ['view']},
}


def _permisos(definicion):
    ids = []
    for app, modelos in definicion.items():
        for modelo, acciones in modelos.items():
            for accion in acciones:
                perm = Permission.objects.filter(
                    content_type__app_label=app, codename=f'{accion}_{modelo}').first()
                if perm:
                    ids.append(perm.id)
    return ids


CATEGORIAS_BASE = [
    'Alimentos', 'Bebidas', 'Aseo del hogar', 'Cuidado personal',
    'Electrónica', 'Juguetes', 'Papelería', 'Otros',
]


def crear_categorias_base():
    from catalog.models import Category
    if not Category.objects.exists():
        Category.objects.bulk_create([Category(name=n) for n in CATEGORIAS_BASE])


def preparar_acceso():
    admin_group, _ = Group.objects.get_or_create(name=GRUPO_ADMIN)
    operador, _ = Group.objects.get_or_create(name=GRUPO_OPERADOR)
    consulta, _ = Group.objects.get_or_create(name=GRUPO_CONSULTA)

    # Los permisos base solo se asignan si el grupo está vacío, para respetar lo que edite el admin
    if admin_group.permissions.count() == 0:
        admin_group.permissions.set(Permission.objects.filter(
            content_type__app_label__in=['catalog', 'inventory', 'vision']))
    if operador.permissions.count() == 0:
        operador.permissions.set(_permisos(PERMISOS_OPERADOR))
    if consulta.permissions.count() == 0:
        consulta.permissions.set(_permisos(PERMISOS_CONSULTA))

    user, nuevo = User.objects.get_or_create(
        username=settings.DEFAULT_ADMIN_USERNAME,
        defaults={'email': settings.DEFAULT_ADMIN_EMAIL, 'first_name': 'Administrador'},
    )
    if nuevo:
        user.set_password(settings.DEFAULT_ADMIN_PASSWORD)
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.save()
    user.groups.add(admin_group)
    crear_categorias_base()
