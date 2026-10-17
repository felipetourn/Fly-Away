from django.urls import path

from .views import PasajeDetalleView, ReservaDetalleView, ReservasView, TicketPdfView

urlpatterns = [
    path('reservas/', ReservasView.as_view()),
    path('reservas/mias/', ReservasView.as_view()),
    path('reservas/<uuid:pk>/', ReservaDetalleView.as_view()),
    path('pasajes/<str:codigo>/', PasajeDetalleView.as_view()),
    path('pasajes/<str:codigo>/pdf/', TicketPdfView.as_view()),
]

