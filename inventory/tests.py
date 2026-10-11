from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product

from .models import Alert, StockMovement
from .services import StockError, apply_movement


class InventarioTests(TestCase):
    def setUp(self):
        self.admin = User.objects.get(username='admin')
        self.producto = Product.objects.create(
            name='Arroz', category=Category.objects.create(name='Granos'),
            price=3500, stock=20, min_stock=5)

    def test_entrada_y_salida_actualizan_stock(self):
        apply_movement(self.producto.pk, StockMovement.IN, 10, user=self.admin)
        apply_movement(self.producto.pk, StockMovement.OUT, 5, user=self.admin)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 25)

    def test_salida_mayor_al_stock_se_rechaza(self):
        with self.assertRaises(StockError):
            apply_movement(self.producto.pk, StockMovement.OUT, 99)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 20)

    def test_alerta_stock_bajo_se_crea_y_se_resuelve(self):
        apply_movement(self.producto.pk, StockMovement.ADJUST, 3)
        self.assertTrue(Alert.objects.filter(
            product=self.producto, kind=Alert.LOW_STOCK, is_resolved=False).exists())
        apply_movement(self.producto.pk, StockMovement.ADJUST, 0)
        self.assertTrue(Alert.objects.filter(kind=Alert.OUT_OF_STOCK, is_resolved=False).exists())
        self.assertFalse(Alert.objects.filter(kind=Alert.LOW_STOCK, is_resolved=False).exists())
        apply_movement(self.producto.pk, StockMovement.IN, 50)
        self.assertFalse(Alert.objects.filter(is_resolved=False).exists())

    def test_vistas_responden(self):
        self.client.login(username='admin', password='admin2026')
        for nombre in ('movement_list', 'movement_create', 'alert_list'):
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)
        r = self.client.post(reverse('movement_create'), {
            'product': self.producto.pk, 'movement_type': 'OUT', 'quantity': 500, 'description': ''})
        self.assertEqual(r.status_code, 200)  # vuelve al formulario con el error
        self.assertContains(r, 'No hay suficiente stock')
