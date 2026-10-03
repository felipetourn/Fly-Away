from django.urls import path

from .views import RegistroPasajeroView, UsuarioActualView

urlpatterns = [
    path('registro/', RegistroPasajeroView.as_view(), name='registro-pasajero'),
    path('yo/', UsuarioActualView.as_view(), name='usuario-actual'),
]
