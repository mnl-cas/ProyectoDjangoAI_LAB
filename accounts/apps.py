from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _preparar_acceso(sender, **kwargs):
    # Se ejecuta tras cada migrate: crea grupos, permisos y el usuario admin
    from .setup import preparar_acceso
    preparar_acceso()


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        # Sin sender: así corre después de migrar todas las apps (los permisos ya existen)
        post_migrate.connect(_preparar_acceso, dispatch_uid='accounts_preparar_acceso')
