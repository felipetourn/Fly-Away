from django.urls import path

from . import views

urlpatterns = [
    path('', views.PagosView.as_view()),
    path('tarjeta/', views.PagoTarjetaView.as_view()),
    path('mercadopago/', views.PagoMercadoPagoView.as_view()),
    # str y no uuid: un id inválido llega a la vista y responde 404 en JSON.
    path('<str:pk>/', views.PagoDetalleView.as_view()),
]
