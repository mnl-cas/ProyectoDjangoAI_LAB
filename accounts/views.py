from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group, Permission, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .permissions import solo_admin
from .setup import GRUPO_CONSULTA

# Grupos que no se pueden borrar ni renombrar porque el sistema depende de ellos
GRUPOS_PROTEGIDOS = ('Administrador', 'Operador', 'Consulta')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    error = None
    username = ''
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenido, {user.first_name or user.username}.')
                destino = request.GET.get('next', '')
                if url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
                    return redirect(destino)
                return redirect('home')
            error = 'Usuario o contraseña incorrectos.'
        else:
            error = 'Por favor, completa los campos.'

    return render(request, 'registration/login.html', {'error': error, 'username': username})


def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    errors = []
    data = {}

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        data = {'username': username, 'email': email,
                'first_name': first_name, 'last_name': last_name}

        if not username or not password1:
            errors.append('Usuario y contraseña son obligatorios.')
        elif password1 != password2:
            errors.append('Las contraseñas no coinciden.')
        elif User.objects.filter(username__iexact=username).exists():
            errors.append('Ese nombre de usuario ya existe.')
        elif email and User.objects.filter(email__iexact=email).exists():
            errors.append('Ese correo electrónico ya está registrado.')
        else:
            try:
                validate_password(password1)
            except ValidationError as e:
                errors.extend(e.messages)

        if not errors:
            user = User.objects.create_user(
                username=username, email=email, password=password1,
                first_name=first_name, last_name=last_name)
            group, _ = Group.objects.get_or_create(name=GRUPO_CONSULTA)
            user.groups.add(group)
            login(request, user)
            messages.success(request, 'Tu cuenta fue creada correctamente.')
            return redirect('home')

    return render(request, 'registration/register.html', {'errors': errors, 'data': data})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'Cerraste sesión.')
    return redirect('login')


# ---------- Usuarios ----------

@solo_admin
def usuarios(request):
    lista = User.objects.prefetch_related('groups').order_by('username')
    return render(request, 'usuarios.html', {'usuarios': lista})


@solo_admin
@require_POST
def cambiar_estado_usuario(request, id_user):
    user = get_object_or_404(User, id=id_user)
    if user == request.user:
        messages.error(request, 'No puedes desactivar tu propia cuenta.')
    else:
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        estado = 'activado' if user.is_active else 'desactivado'
        messages.success(request, f'Usuario {user.username} {estado}.')
    return redirect('usuarios')


# ---------- Grupos ----------

@solo_admin
def grupos(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre_grupo', '').strip()
        if not nombre:
            messages.error(request, 'El nombre del grupo es obligatorio.')
        elif Group.objects.filter(name__iexact=nombre).exists():
            messages.error(request, f'El grupo «{nombre}» ya existe.')
        else:
            Group.objects.create(name=nombre)
            messages.success(request, f'Grupo «{nombre}» creado.')
        return redirect('grupos')

    lista = Group.objects.prefetch_related('permissions', 'user_set').order_by('name')
    return render(request, 'grupos.html', {'grupos': lista, 'protegidos': GRUPOS_PROTEGIDOS})


@solo_admin
@require_POST
def eliminar_grupo(request, id_grupo):
    grupo = get_object_or_404(Group, id=id_grupo)
    if grupo.name in GRUPOS_PROTEGIDOS:
        messages.error(request, f'El grupo «{grupo.name}» es del sistema y no se puede eliminar.')
    else:
        grupo.delete()
        messages.success(request, f'Grupo «{grupo.name}» eliminado.')
    return redirect('grupos')


@solo_admin
def editar_grupo(request, id_grupo):
    grupo = get_object_or_404(Group, id=id_grupo)

    if request.method == 'POST':
        nuevo_nombre = request.POST.get('name', '').strip()
        if grupo.name in GRUPOS_PROTEGIDOS and nuevo_nombre != grupo.name:
            messages.error(request, 'Los grupos del sistema no se pueden renombrar.')
        elif not nuevo_nombre:
            messages.error(request, 'El nombre no puede estar vacío.')
        elif Group.objects.filter(name__iexact=nuevo_nombre).exclude(id=grupo.id).exists():
            messages.error(request, f'Ya existe un grupo llamado «{nuevo_nombre}».')
        else:
            grupo.name = nuevo_nombre
            grupo.save()
            messages.success(request, 'Grupo actualizado.')
            return redirect('grupos')
        return redirect('editar_grupo', id_grupo=grupo.id)

    miembros = grupo.user_set.order_by('username')
    no_miembros = User.objects.exclude(groups=grupo).order_by('username')
    return render(request, 'editar_grupo.html', {
        'grupo': grupo,
        'miembros': miembros,
        'no_miembros': no_miembros,
        'protegido': grupo.name in GRUPOS_PROTEGIDOS,
    })


@solo_admin
@require_POST
def agregar_usuario_grupo(request, id_grupo):
    grupo = get_object_or_404(Group, id=id_grupo)
    id_user = request.POST.get('id_user')
    if id_user:
        user = get_object_or_404(User, id=id_user)
        grupo.user_set.add(user)
        messages.success(request, f'{user.username} se agregó a «{grupo.name}».')
    return redirect('editar_grupo', id_grupo=grupo.id)


@solo_admin
@require_POST
def eliminar_usuario_grupo(request, id_grupo):
    grupo = get_object_or_404(Group, id=id_grupo)
    id_user = request.POST.get('id_user')
    if id_user:
        user = get_object_or_404(User, id=id_user)
        grupo.user_set.remove(user)
        messages.success(request, f'{user.username} salió de «{grupo.name}».')
    return redirect('editar_grupo', id_grupo=grupo.id)


# ---------- Permisos ----------

APPS_GESTIONADAS = ('catalog', 'inventory', 'vision')


@solo_admin
def permisos(request):
    grupos_qs = Group.objects.order_by('name')
    grupo_id = request.POST.get('grupo') or request.GET.get('grupo')
    grupo = get_object_or_404(Group, id=grupo_id) if grupo_id else grupos_qs.first()

    todos = (Permission.objects
             .filter(content_type__app_label__in=APPS_GESTIONADAS)
             .select_related('content_type')
             .order_by('content_type__app_label', 'content_type__model', 'codename'))

    if request.method == 'POST' and grupo:
        ids = [int(i) for i in request.POST.getlist('permisos') if i.isdigit()]
        grupo.permissions.set(todos.filter(id__in=ids))
        messages.success(request, f'Permisos de «{grupo.name}» actualizados.')
        return redirect(f"{reverse('permisos')}?grupo={grupo.id}")

    permisos_grupo = set(grupo.permissions.values_list('id', flat=True)) if grupo else set()

    # Agrupados por modelo para mostrarlos ordenados
    secciones = {}
    for p in todos:
        modelo = p.content_type.model_class()
        etiqueta = modelo._meta.verbose_name_plural.title() if modelo else p.content_type.model
        secciones.setdefault(etiqueta, []).append(p)

    return render(request, 'permisos.html', {
        'secciones': secciones,
        'grupos': grupos_qs,
        'grupo': grupo,
        'permisos_grupo': permisos_grupo,
    })
