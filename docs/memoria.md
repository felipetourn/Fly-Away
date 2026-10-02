# Memoria del proyecto

Registro vivo: qué está hecho, qué se decidió y por qué, qué falta. Actualizar al cerrar cada tarea (lo más nuevo arriba en cada sección).

## Estado actual

**2026-10-02 — Calendario de rango y logo de la card (rama `fix/logo-card-y-calendario`)**
- El buscador tiene una caja por tramo: "Fechas" en solo ida; "Ida" y "Vuelta" en ida y vuelta. Cada caja abre un calendario (`SelectorFechas`, con react-day-picker): primer clic = inicio, segundo = fin, el mismo día = un solo día. La lógica de búsqueda, la URL y el backend no cambian.
- La card de resultados usa `logoA`, como el detalle.

**2026-10-02 — Backend de vuelos (rama `feat/backend-vuelos`)**
- Modelo `usuarios` del DBML (login por email, `rol`), que reemplaza a `accounts`. **Para la US de login:** el modelo ya está; faltan `POST /auth/registro/`, `GET /auth/yo/` y conectar `auth.ts`/`sesion.tsx` (hoy mock).
- App `vuelos`: aeropuertos, aviones y vuelos con los constraints del DBML; `GET /api/aeropuertos/`, `/api/vuelos/buscar/` y `/api/vuelos/{id}/`. El front ya no usa el mock de vuelos.
- Búsqueda sin límite de días; en ida y vuelta, la ida y la vuelta aceptan fecha exacta o rango.
- `python manage.py seed`: datos de ejemplo. Corre en `build.sh` (Render free no tiene shell).
- **Supabase reseteada (2026-10-02)** y preparada para esta rama: `migrate` + `seed` aplicados (11 aeropuertos, 4 aviones, 13 124 vuelos); constraints y API verificados contra Postgres. Hasta el merge, el backend de `main` en Render no encuentra las tablas de `accounts` (admin/login caídos; el front usa mock, no se entera).
- **Local:** si `backend/.env` tiene `DATABASE_URL` de Supabase, correr tests/seed/runserver con `DATABASE_URL=` (SQLite) para no tocar la BD compartida.

**2026-10-02 — Detalle de vuelo, US05 (rama `feat/detalle-vuelo`)**
- Cada card de resultados tiene "Ver detalle" y "Elegir". El detalle es un diálogo (`<dialog>` nativo) con origen, destino, horarios, fecha, clases, precio por clase, disponibilidad y avión; se puede elegir el vuelo desde ahí.
- Mock: `getVuelo(id)` (futuro `GET /vuelos/{id}/`), avión por ruta y números de vuelo únicos por ruta y fecha.

**2026-10-02 — Interfaz de inicio (rama `feat/interfaz-inicio`)**
- Pantalla `/` del pasajero: header con sesión, hero con carrusel de destinos, buscador y resultados.
- Búsqueda según los criterios de la US: en **Solo ida** origen y/o destino y fecha o rango (≤ 14 días); en **Ida y vuelta**, flujo en dos pasos (ida → vuelta). Filtro de rango de precio sobre los resultados.
- Vuelos ya conectados al backend (ver arriba); la sesión (`lib/auth.ts`) sigue mockeada.
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
| 2026-10-02 | `react-day-picker` para elegir el rango en un mismo calendario | `<input type="date">` no elige rangos; la librería trae accesibilidad (teclado, lectores) y español resueltos |
| 2026-10-02 | Sin límite de días en el rango de búsqueda; rango también en ida y vuelta | Pedido del equipo: elegir ida y vuelta en una fecha o entre dos |
| 2026-10-02 | Errores 400 con el formato de DRF (`{"param": ["mensaje"]}`) en español | Estándar del framework; el front puede ubicar cada error en su campo |
| 2026-10-02 | `seed` en `build.sh`, idempotente con `ignore_conflicts` | Render free no tiene shell; hasta que exista el ABM de vuelos no hay otra forma de cargar datos |
| 2026-10-02 | `Usuario` sin `PermissionsMixin`; el admin de Django es solo para `administrador` | El DBML no tiene tablas de permisos; el rol define el acceso |
| 2026-10-02 | API sin versionar (`/api/`, no `/api/v1/`) | Un solo cliente (nuestro front) que se despliega junto; agregar `v1` después es cambiar el prefijo y `VITE_API_URL` |
| 2026-10-02 | Detalle de vuelo en un diálogo sobre los resultados, sin ruta propia | Solo se llega a un vuelo buscándolo; el diálogo no saca al pasajero del flujo de ida y vuelta |
| 2026-10-02 | El detalle pide los datos de nuevo (`getVuelo`) al abrirse | Los asientos pueden cambiar desde la búsqueda y el detalle trae el avión |
| 2026-10-02 | Mock: bloque de números de vuelo por ruta | Respeta el índice único (`numero_vuelo`, `fecha_operacion`) y permite reconstruir el vuelo desde su id |
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

1. Mergear `feat/backend-vuelos` a `main` (Supabase ya está lista) y crear el superusuario con `createsuperuser`.
2. ABM de vuelos (admin), con generación de N filas a partir de días + período. Al terminarlo, sacar `seed` de `build.sh`.
3. Compra: cerrar los pendientes del modelo (arriba) y sumar reservas + pasajes + pagos + emails.
4. Reportes de ocupación.
5. Notificaciones por cambio de horario / cancelación.
