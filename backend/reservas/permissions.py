from rest_framework.permissions import BasePermission


class EsPasajero(BasePermission):
    """Reservar pasajes como usuario online corresponde al rol pasajero."""

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.rol == 'pasajero')

