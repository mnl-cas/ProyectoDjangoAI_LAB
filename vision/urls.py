from django.urls import path

from . import views

urlpatterns = [
    path('', views.inspection_create, name='inspection_create'),
    path('historial/', views.inspection_list, name='inspection_list'),
    path('<int:pk>/', views.inspection_detail, name='inspection_detail'),
    path('<int:pk>/aplicar/', views.inspection_apply, name='inspection_apply'),
    path('<int:pk>/eliminar/', views.inspection_delete, name='inspection_delete'),
]
