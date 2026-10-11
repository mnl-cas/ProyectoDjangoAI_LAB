from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('registro/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('usuarios/', views.usuarios, name='usuarios'),
    path('usuarios/<int:id_user>/estado/', views.cambiar_estado_usuario, name='cambiar_estado_usuario'),
    path('grupos/', views.grupos, name='grupos'),
    path('grupos/<int:id_grupo>/eliminar/', views.eliminar_grupo, name='eliminar_grupo'),
    path('grupos/<int:id_grupo>/editar/', views.editar_grupo, name='editar_grupo'),
    path('grupos/<int:id_grupo>/agregar-usuario/', views.agregar_usuario_grupo, name='agregar_usuario_grupo'),
    path('grupos/<int:id_grupo>/eliminar-usuario/', views.eliminar_usuario_grupo, name='eliminar_usuario_grupo'),
    path('permisos/', views.permisos, name='permisos'),
]
