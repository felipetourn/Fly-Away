from rest_framework.permissions import BasePermission


class EsAdministrador(BasePermission):
    """El ABM es del rol administrador. Sin sesión, DRF responde 401; con otro rol, 403."""

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.rol == 'administrador')
