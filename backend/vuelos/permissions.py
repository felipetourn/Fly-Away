from rest_framework.permissions import BasePermission


class EsAdministrador(BasePermission):
    """El ABM es del rol administrador. Sin sesión, DRF responde 401; con otro rol, 403."""

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.rol == 'administrador')


class EsEmpleadoMostrador(BasePermission):
    """Consultas operativas desde mostrador corresponden al rol empleado_mostrador. Sin sesión: 401; otro rol: 403."""

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.rol == 'empleado_mostrador')
