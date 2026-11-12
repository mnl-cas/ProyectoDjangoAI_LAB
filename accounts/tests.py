from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.urls import reverse


class RegistroYAccesoTests(TestCase):
    def test_registro_crea_usuario_sin_permisos(self):
        r = self.client.post(reverse('registro'), {
            'username': 'ana', 'email': 'ana@example.com', 'first_name': 'Ana',
            'password1': 'Clave-segura-91', 'password2': 'Clave-segura-91'})
        self.assertRedirects(r, reverse('home'))
        self.assertFalse(User.objects.get(username='ana').groups.exists())

    def test_login_y_logout(self):
        User.objects.create_user('luis', password='Clave-segura-91')
        r = self.client.post(reverse('login'), {'username': 'luis', 'password': 'Clave-segura-91'})
        self.assertRedirects(r, reverse('home'))
        self.client.post(reverse('logout'))
        self.assertEqual(self.client.get(reverse('home')).status_code, 302)

    def test_usuario_sin_permisos_no_puede_crear_productos_ni_administrar(self):
        user = User.objects.create_user('lector', password='Clave-segura-91')
        user.user_permissions.add(Permission.objects.get(codename='view_product'))
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('product_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('product_create')).status_code, 403)
        self.assertEqual(self.client.get(reverse('grupos')).status_code, 302)

    def test_admin_gestiona_grupos_y_permisos(self):
        User.objects.create_superuser('admin', password='admin2026')
        self.client.login(username='admin', password='admin2026')
        self.client.post(reverse('grupos'), {'nombre_grupo': 'Bodega'})
        grupo = Group.objects.get(name='Bodega')
        self.assertEqual(self.client.get(reverse('editar_grupo', args=[grupo.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse('permisos')).status_code, 200)
        perm = Permission.objects.get(codename='view_product')
        self.client.post(reverse('permisos'), {'grupo': grupo.id, 'permisos': [perm.id]})
        self.assertEqual(list(grupo.permissions.all()), [perm])
        self.client.post(reverse('eliminar_grupo', args=[grupo.id]))
        self.assertFalse(Group.objects.filter(name='Bodega').exists())
