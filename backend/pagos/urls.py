from django.urls import path

from . import views

urlpatterns = [
    path('reservas/', views.ReservasView.as_view()),
]
