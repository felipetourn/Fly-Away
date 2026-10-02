from django.urls import path

from . import views

urlpatterns = [
    path('aeropuertos/', views.AeropuertosView.as_view()),
    # str y no uuid: un id inválido llega a DRF y responde 404 en JSON.
    path('vuelos/<str:pk>/', views.VueloDetalleView.as_view()),
]
