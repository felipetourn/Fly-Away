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
| 2026-09-26 | Modelo relacional definido en `docs/modelo.dbml` (fuente de verdad); nombres en español | Diseño del equipo; código y BD usan los mismos nombres |
| 2026-09-26 | Usuario custom desde el inicio (hoy `accounts.User` provisorio → se reemplaza por `usuarios`) | Cambiar el modelo de usuario con datos cargados es muy costoso; hoy no hay datos |
| 2026-09-26 | JWT (SimpleJWT) en vez de sesiones | Front y back en dominios distintos (Vercel/Render); evita problemas de cookies cross-site |
| 2026-09-26 | Sin `DATABASE_URL` → SQLite local | Poder desarrollar sin conexión a Supabase |
| 2026-09-26 | Una fila en `vuelos` por fecha, sin tabla de recurrencia | Cancelar/modificar una fecha puntual no afecta a las demás (US02, US03) |
| 2026-09-26 | `asientos_disponibles_*` como contador, descontado con `select_for_update()` | Disponibilidad y ocupación sin contar pasajes; el lock evita sobreventa |
| 2026-09-26 | Comprador (`reservas.pasajero_id`) ≠ viajero (datos en `pasajes`) | Se pueden comprar hasta 9 pasajes para otras personas |
| 2026-09-26 | Solo web (sin app móvil), responsive | Alcance definido por el equipo |

## Pendientes / a definir

- [ ] **Pagos:** ¿simulados (form de tarjeta que se valida y se registra) o pasarela real (Mercado Pago sandbox)? Propuesta: simulado.
- [ ] **Proveedor de email en prod:** verificar si el plan free de Render permite SMTP saliente; si no, usar la API HTTP de un proveedor (Resend, Brevo, etc.).
- [ ] **PDF de pasajes/factura:** elegir librería (p. ej. `reportlab`) cuando se implemente.
- [ ] **Periodo de venta:** el modelo lo toma como "fechas en que opera". Si la cátedra lo entiende como "desde cuándo se puede comprar", falta un campo (ej. `venta_desde`). Confirmar con el docente.
- [ ] **Venta en mostrador a alguien sin cuenta:** ¿quién queda en `reservas.pasajero_id`? Opciones: crear la cuenta en el momento, o agregar `vendido_por` + datos de contacto del comprador.
- [ ] **Ida y vuelta:** son 2 reservas; si se pagan juntas, `pagos` hoy apunta a una sola reserva. Si el alcance es solo ida, no aplica.
- [ ] **Sugerencias al modelo** (no aplicadas): único (`numero_vuelo`, `fecha_operacion`); `CheckConstraint` para 1..9 pasajes y origen ≠ destino; `cantidad_pasajes` duplica el conteo de `pasajes` (mantener sincronizado).
- [ ] ¿El empleado de mostrador puede cancelar/modificar reservas?

## Próximos pasos

1. Cerrar los pendientes del modelo (arriba) e implementarlo en Django; resetear la BD de Supabase (hoy tiene las tablas provisorias de `accounts`).
2. ABM de vuelos (admin), con generación de N filas a partir de días + período.
3. Búsqueda de vuelos con disponibilidad.
4. Compra: reservas + pasajes + pagos + emails.
5. Reportes de ocupación.
6. Notificaciones por cambio de horario / cancelación.
