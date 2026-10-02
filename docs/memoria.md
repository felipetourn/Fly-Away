# Memoria del proyecto

Registro vivo: qué está hecho, qué se decidió y por qué, qué falta. Actualizar al cerrar cada tarea (lo más nuevo arriba en cada sección).

## Estado actual

**2026-10-02 — Interfaz de inicio (rama `feat/interfaz-inicio`)**
- Pantalla `/` del pasajero: header con sesión, hero con carrusel de destinos, buscador y resultados.
- Búsqueda según los criterios de la US: en **Solo ida** origen y/o destino y fecha o rango (≤ 14 días); en **Ida y vuelta**, flujo en dos pasos (ida → vuelta). Filtro de rango de precio sobre los resultados.
- **Todo mockeado** en `frontend/src/lib/vuelos.ts` y `lib/auth.ts`, con la forma de la API. Conectar el back = reemplazar el cuerpo de `getAeropuertos`, `buscarVuelos` y `usuarioActual` por `api(...)`.
- Páginas `/reservas`, `/perfil`, `/login`, `/registro` vacías ("Próximamente"); `/login` tiene "Entrar (demo)".
- Chequeos de lógica pura: `npm run check` (Node + assert, sin framework).

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
| 2026-10-02 | Front de búsqueda con datos mock que respetan el contrato del back | Avanzar la UI sin bloquearse con el modelo; cambiar a la API toca solo `src/lib/` |
| 2026-10-02 | Avatar con iniciales (sin foto) | `usuarios` no tiene campo de foto; evita subir archivos |
| 2026-10-02 | Ida y vuelta = dos pasos (elegir ida, después vuelta) | Cada fila de `vuelos` es un tramo; coincide con el endpoint de búsqueda |
| 2026-10-02 | Estado de búsqueda en la query string | Funcionan "atrás" y recargar |
| 2026-10-02 | "Solo ida" funciona como explorador (origen/destino opcionales, rango de fechas); "Ida y vuelta" pide ruta y fechas exactas | Cumple los criterios de la US sin perder el flujo de ida y vuelta; una vuelta sin los dos extremos no tiene sentido |
| 2026-10-02 | El rango de precio y "ya salió" los filtra el backend (`precio_min`, `precio_max` en `/vuelos/buscar/`) | El front no filtra resultados por su cuenta: el mock aplica la misma regla que el endpoint |
| 2026-10-02 | `modelo.dbml` actualizado: `reservas.vendido_por`, `contacto_email`, `contacto_nombre`, `pasajero_id` opcional, índice único (`numero_vuelo`, `fecha_operacion`), CHECKs | Resuelve la venta en mostrador a alguien sin cuenta |
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
- [ ] **Ida y vuelta:** son 2 reservas; si se pagan juntas, `pagos` hoy apunta a una sola reserva. Si el alcance es solo ida, no aplica.
- [ ] **Ida y vuelta en la compra:** el front ya permite elegir ida + vuelta; al implementar la compra definir si son 2 reservas con un pago cada una o un pago para ambas (`pagos.reserva_id` hoy apunta a una sola).
- [ ] ¿El empleado de mostrador puede cancelar/modificar reservas?

## Próximos pasos

1. Cerrar los pendientes del modelo (arriba) e implementarlo en Django; resetear la BD de Supabase (hoy tiene las tablas provisorias de `accounts`).
2. ABM de vuelos (admin), con generación de N filas a partir de días + período.
3. Búsqueda de vuelos con disponibilidad.
4. Compra: reservas + pasajes + pagos + emails.
5. Reportes de ocupación.
6. Notificaciones por cambio de horario / cancelación.
