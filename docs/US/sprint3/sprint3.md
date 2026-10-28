# Sprint 3 - Resumen

Objetivo del sprint: completar y robustecer las funcionalidades operativas de Fly Away: consistencia de las compras concurrentes, consulta y reporte de la ocupación de los vuelos, información operativa para el empleado de mostrador y notificaciones a los pasajeros ante cambios de horario o cancelaciones.

## User stories

| US | Nombre | Story points | Horas estimadas | Horas reales | Estado | Ficha |
|---|---|---|---|---|---|---|
| US11 | Gestionar compras concurrentes de pasajes | 13 | 25 | — | Terminada | [us11.md](us11.md) |
| US12 | Consultar ocupación | 3 | 12 | — | Terminada | [us12.md](us12.md) |
| US13 | Generar reporte de ocupación | 3 | 13 | — | Pendiente | |
| US14 | Consultar estado de un vuelo desde mostrador | 5 | 14 | — | A cargo de otro integrante | |
| US15 | Notificar modificaciones de horario | 5 | 16 | — | A cargo de otro integrante | |
| US16 | Notificar cancelaciones | 5 | 14 | — | A cargo de otro integrante | |
| **Total** | | **34** | **94** | | | |

## Correr en local

- La rama `feat/sprint3-concurrencia-ocupacion` (US11 a US13) **no agrega migraciones**.
- Los vuelos de ejemplo cambiaron (ventas reales): para limpiar una base vieja, `DATABASE_URL= .venv/bin/python manage.py seed --regenerar`.
- Las pruebas concurrentes de la US11 necesitan Postgres: ver [us11.md](us11.md#cómo-probarlo).
