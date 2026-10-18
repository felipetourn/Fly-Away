from django.urls import path

from .views import PasajeDetalleView, ReservaDetalleView, ReservaIdaVueltaView, ReservasView, TicketPdfView

urlpatterns = [
    path('reservas/ida-vuelta/', ReservaIdaVueltaView.as_view()),
    path('reservas/', ReservasView.as_view()),
    path('reservas/<uuid:pk>/', ReservaDetalleView.as_view()),
    path('pasajes/<str:codigo>/', PasajeDetalleView.as_view()),
    path('pasajes/<str:codigo>/pdf/', TicketPdfView.as_view()),
]
