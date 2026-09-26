# Memoria del proyecto

Registro vivo: qué está hecho, qué se decidió y por qué, qué falta. Actualizar al cerrar cada tarea (lo más nuevo arriba en cada sección).

## Estado actual

**2026-09-26 — Deploy funcionando** (front → back → BD verificado con `/api/health/`)
- Repo: https://github.com/felipetourn/Fly-Away (rama `main`, auto-deploy en Render y Vercel)
- Frontend (Vercel): https://fly-away-one.vercel.app — env: `VITE_API_URL` (requiere redeploy al cambiarla)
- Backend (Render, Virginia, free): https://fly-away-iz7s.onrender.com — env: `SECRET_KEY`, `DEBUG`, `PYTHON_VERSION`, `DATABASE_URL`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`
- BD (Supabase): conexión por **Session pooler** (puerto 5432). Contraseña sin caracteres especiales (rompen la URL).
- Render free se duerme tras ~15 min: abrir `/api/health/` antes de una demo.
- La BD de Supabase tiene las tablas del setup (`accounts`). Al implementar el modelo relacional definitivo hay que **resetearla** (no hay datos reales).

**2026-09-26 — Setup inicial**
- Backend Django creado (`config/`, app `accounts` con `User` custom + `role`), migrado en SQLite local.
- Endpoints: `/api/health/`, `/api/auth/token/`, `/api/auth/token/refresh/`.
- Frontend Vite + React + TS + Tailwind v4 + react-router; rutas vacías `/`, `/mostrador`, `/admin`. Build OK.
- Archivos de deploy: `backend/build.sh` (Render), `frontend/vercel.json` (Vercel).

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

1. App `flights`: modelos `Airport`, `Flight` + ABM (admin).
2. Búsqueda de vuelos con disponibilidad.
3. App `bookings`: compra + pago + emails.
4. Reportes de ocupación.
