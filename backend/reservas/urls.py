from django.urls import path

from .views import ReservaDetalleView, ReservasView

urlpatterns = [
    path('reservas/', ReservasView.as_view()),
    path('reservas/mias/', ReservasView.as_view()),
    path('reservas/<uuid:pk>/', ReservaDetalleView.as_view()),
]

