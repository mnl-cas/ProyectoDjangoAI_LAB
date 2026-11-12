import io
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from catalog.models import Product

from .models import Inspection


def _imagen(color=(200, 200, 200)):
    buffer = io.BytesIO()
    Image.new('RGB', (640, 480), color).save(buffer, format='JPEG')
    return SimpleUploadedFile('foto.jpg', buffer.getvalue(), content_type='image/jpeg')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class VisionTests(TestCase):
    def setUp(self):
        User.objects.create_superuser('admin', password='admin2026')
        self.client.login(username='admin', password='admin2026')

    def test_paginas_cargan(self):
        for nombre in ('home', 'inspection_create', 'inspection_list', 'product_list',
                       'category_list', 'usuarios', 'grupos', 'permisos'):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)

    def test_analisis_con_el_modelo_yolo_real(self):
        r = self.client.post(reverse('inspection_create'), {'image': _imagen()})
        inspection = Inspection.objects.get()
        self.assertRedirects(r, reverse('inspection_detail', args=[inspection.pk]))
        self.assertTrue(inspection.annotated_image)
        self.assertEqual(self.client.get(reverse('inspection_detail', args=[inspection.pk])).status_code, 200)

    def test_archivo_no_imagen_se_rechaza(self):
        falso = SimpleUploadedFile('x.jpg', b'no soy una imagen', content_type='image/jpeg')
        r = self.client.post(reverse('inspection_create'), {'image': falso})
        self.assertRedirects(r, reverse('inspection_create'))
        self.assertEqual(Inspection.objects.count(), 0)

    def test_sin_modelo_yolo_el_analisis_sigue_funcionando(self):
        from visionstock_project.ia import buscador
        guardado, buscador.YOLO = buscador.YOLO, None
        self.addCleanup(setattr, buscador, 'YOLO', guardado)
        archivo = dict(buscador.CONFIG)
        buscador.CONFIG['yolo_archivo'] = 'no_existe.pt'
        self.addCleanup(buscador.CONFIG.update, archivo)
        r = self.client.post(reverse('inspection_create'), {'image': _imagen()}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Inspection.objects.count(), 1)  # OWLv2 + DINOv2 cubren la falta de YOLO
