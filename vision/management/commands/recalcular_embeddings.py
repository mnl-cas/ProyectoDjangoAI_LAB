from django.core.management.base import BaseCommand
from PIL import Image

from catalog.models import ReferenceImage
from vision.services import reference_vectors


class Command(BaseCommand):
    help = 'Recalcula los embeddings de todas las imágenes de referencia (tras mejorar el modelo).'

    def handle(self, *args, **options):
        total = 0
        for ref in ReferenceImage.objects.select_related('product'):
            try:
                with Image.open(ref.image.path) as img:
                    ref.embedding = reference_vectors(img)
            except (OSError, ValueError) as e:
                self.stderr.write(f'{ref}: {e}')
                continue
            ref.save(update_fields=['embedding'])
            total += 1
            self.stdout.write(f'{ref.product.name}: {len(ref.embedding)} vectores')
        self.stdout.write(self.style.SUCCESS(f'{total} referencias actualizadas.'))
