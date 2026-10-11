from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse


class AdminPorDefectoTests(TestCase):
    def test_admin_existe_con_clave_por_defecto(self):
        admin = User.objects.get(username='admin')
        self.assertTrue(admin.is_superuser and admin.is_staff)
        self.assertTrue(admin.check_password('admin2026'))

    def test_grupos_base_con_permisos(self):
        for nombre in ('Administrador', 'Operador', 'Consulta'):
            self.assertTrue(Group.objects.get(name=nombre).permissions.exists(), nombre)


class RegistroYAccesoTests(TestCase):
    def test_registro_asigna_grupo_consulta(self):
        r = self.client.post(reverse('register'), {
            'username': 'ana', 'email': 'ana@example.com', 'first_name': 'Ana',
            'password1': 'Clave-segura-91', 'password2': 'Clave-segura-91'})
        self.assertRedirects(r, reverse('home'))
        self.assertTrue(User.objects.get(username='ana').groups.filter(name='Consulta').exists())

    def test_consulta_no_puede_crear_productos_ni_administrar(self):
        user = User.objects.create_user('lector', password='Clave-segura-91')
        user.groups.add(Group.objects.get(name='Consulta'))
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('product_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('product_create')).status_code, 403)
        self.assertEqual(self.client.get(reverse('grupos')).status_code, 302)

    def test_admin_gestiona_grupos_y_permisos(self):
        self.client.login(username='admin', password='admin2026')
        self.client.post(reverse('grupos'), {'nombre_grupo': 'Bodega'})
        grupo = Group.objects.get(name='Bodega')
        self.assertEqual(self.client.get(reverse('editar_grupo', args=[grupo.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse('permisos')).status_code, 200)
        perm = Group.objects.get(name='Consulta').permissions.first()
        self.client.post(reverse('permisos'), {'grupo': grupo.id, 'permisos': [perm.id]})
        self.assertEqual(list(grupo.permissions.all()), [perm])
        self.client.post(reverse('eliminar_grupo', args=[grupo.id]))
        self.assertFalse(Group.objects.filter(name='Bodega').exists())

    def test_grupos_del_sistema_no_se_eliminan(self):
        self.client.login(username='admin', password='admin2026')
        g = Group.objects.get(name='Operador')
        self.client.post(reverse('eliminar_grupo', args=[g.id]))
        self.assertTrue(Group.objects.filter(name='Operador').exists())
