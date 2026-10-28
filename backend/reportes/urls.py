from django.urls import path

from . import views

urlpatterns = [
    # str y no uuid: un id inválido llega a DRF y responde 404 en JSON.
    path('ocupacion/<str:pk>/', views.OcupacionVueloView.as_view(), name='ocupacion-vuelo'),
]
