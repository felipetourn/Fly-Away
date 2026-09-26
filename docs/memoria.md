# Memoria del proyecto

Registro vivo: qué está hecho, qué se decidió y por qué, qué falta. Actualizar al cerrar cada tarea (lo más nuevo arriba en cada sección).

## Estado actual

**2026-09-26 — Setup inicial**
- Backend Django creado (`config/`, app `accounts` con `User` custom + `role`), migrado en SQLite local.
- Endpoints: `/api/health/`, `/api/auth/token/`, `/api/auth/token/refresh/`.
- Frontend Vite + React + TS + Tailwind v4 + react-router; rutas vacías `/`, `/mostrador`, `/admin`. Build OK.
- Archivos de deploy: `backend/build.sh` (Render), `frontend/vercel.json` (Vercel).
- Todavía **no** se conectó Supabase ni se deployó nada.

## Decisiones

| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-09-26 | `User` custom con campo `role` desde el inicio | Cambiar el modelo de usuario después de la 1ª migración es muy costoso |
| 2026-09-26 | JWT (SimpleJWT) en vez de sesiones | Front y back en dominios distintos (Vercel/Render); evita problemas de cookies cross-site |
| 2026-09-26 | Sin `DATABASE_URL` → SQLite local | Poder desarrollar sin conexión a Supabase |
| 2026-09-26 | Ocupación calculada desde `Ticket` (sin tabla de instancias de vuelo) | Más simple; se agrega `FlightDate` si se necesita cancelar fechas puntuales |
| 2026-09-26 | Solo web (sin app móvil), responsive | Alcance definido por el equipo |

## Pendientes / a definir

- [ ] **Pagos:** ¿simulados (form de tarjeta que se valida y se registra) o pasarela real (Mercado Pago sandbox)? Propuesta: simulado.
- [ ] **Proveedor de email en prod:** verificar si el plan free de Render permite SMTP saliente; si no, usar la API HTTP de un proveedor (Resend, Brevo, etc.).
- [ ] **PDF de pasajes/factura:** elegir librería (p. ej. `reportlab`) cuando se implemente.
- [ ] ¿Cancelación por fecha puntual o solo del vuelo completo?
- [ ] ¿El empleado de mostrador puede cancelar/modificar reservas?

## Próximos pasos

1. Crear repo git y subir a GitHub.
2. App `flights`: modelos `Airport`, `Flight` + ABM (admin).
3. Búsqueda de vuelos con disponibilidad.
4. App `bookings`: compra + pago + emails.
5. Reportes de ocupación.
6. Deploy (Supabase → Render → Vercel).
