from django.contrib import admin

from .models import Aeropuerto, Avion, Vuelo


@admin.register(Aeropuerto)
class AeropuertoAdmin(admin.ModelAdmin):
    list_display = ('codigo_iata', 'ciudad', 'nombre', 'pais')
    search_fields = ('codigo_iata', 'ciudad', 'nombre')


@admin.register(Avion)
class AvionAdmin(admin.ModelAdmin):
    list_display = ('matricula', 'modelo', 'capacidad_economy', 'capacidad_primera')


@admin.register(Vuelo)
class VueloAdmin(admin.ModelAdmin):
    list_display = ('numero_vuelo', 'fecha_operacion', 'hora_partida', 'aeropuerto_origen', 'aeropuerto_destino', 'estado')
    list_filter = ('estado', 'aeropuerto_origen', 'aeropuerto_destino')
    date_hierarchy = 'fecha_operacion'
    search_fields = ('numero_vuelo',)
