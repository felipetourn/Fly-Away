from django.contrib import admin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    # ponytail: sin alta/cambio de contraseña desde el admin; eso llega con la US de login/registro.
    fields = ('email', 'nombre', 'apellido', 'rol', 'activo')
    list_display = ('email', 'nombre', 'apellido', 'rol', 'activo')
    list_filter = ('rol', 'activo')
    search_fields = ('email', 'nombre', 'apellido')
