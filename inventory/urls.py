from django.urls import path

from . import views

urlpatterns = [
    path('', views.movement_list, name='movement_list'),
    path('nuevo/', views.movement_create, name='movement_create'),
    path('alertas/', views.alert_list, name='alert_list'),
    path('alertas/<int:pk>/resolver/', views.alert_resolve, name='alert_resolve'),
]
