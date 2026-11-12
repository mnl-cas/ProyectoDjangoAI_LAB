from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('catalogo/', views.product_list, name='product_list'),
    path('catalogo/nuevo/', views.product_create, name='product_create'),
    path('catalogo/<int:pk>/', views.product_detail, name='product_detail'),
    path('catalogo/<int:pk>/editar/', views.product_edit, name='product_edit'),
    path('catalogo/<int:pk>/eliminar/', views.product_delete, name='product_delete'),
    path('catalogo/<int:pk>/referencias/', views.upload_references, name='upload_references'),
    path('catalogo/referencias/<int:pk>/eliminar/', views.reference_delete, name='reference_delete'),
    path('catalogo/categorias/', views.category_list, name='category_list'),
    path('catalogo/categorias/nueva/', views.category_create, name='category_create'),
    path('catalogo/categorias/<int:pk>/editar/', views.category_edit, name='category_edit'),
    path('catalogo/categorias/<int:pk>/eliminar/', views.category_delete, name='category_delete'),
]
