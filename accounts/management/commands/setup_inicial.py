from django.core.management.base import BaseCommand

from accounts.setup import preparar_acceso


class Command(BaseCommand):
    help = 'Crea los grupos base y el usuario administrador (admin / admin2026).'

    def handle(self, *args, **options):
        preparar_acceso()
        self.stdout.write(self.style.SUCCESS('Grupos y administrador listos.'))
