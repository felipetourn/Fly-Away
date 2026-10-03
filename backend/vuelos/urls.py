from django.urls import path

from . import views

urlpatterns = [
    path('aeropuertos/', views.AeropuertosView.as_view()),
    path('aviones/', views.AvionesView.as_view()),
    path('vuelos/', views.VuelosView.as_view()),
    path('vuelos/buscar/', views.BuscarVuelosView.as_view()),
    path('vuelos/<str:pk>/cancelar/', views.CancelarVueloView.as_view()),
    # str y no uuid: un id inválido llega a DRF y responde 404 en JSON.
    path('vuelos/<str:pk>/', views.VueloDetalleView.as_view()),
]
