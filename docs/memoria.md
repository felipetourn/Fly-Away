# Memoria del proyecto

Registro vivo: qué está hecho, qué se decidió y por qué, qué falta. Actualizar al cerrar cada tarea (lo más nuevo arriba en cada sección).

## Estado actual

**2026-10-18 - US10, factura por la API de Brevo (rama `feat/us10-brevo`)**
- Los mails salen por la API HTTP de Brevo con `django-anymail` (`BREVO_API_KEY`); Render free bloquea el SMTP. Sin la clave, van a la consola.
- `factura.py`: también ataja los errores de anymail (`AnymailError`), sin la rama muerta de reservas demo; los templates usan "-" en lugar de "·".
- En Render: `BREVO_API_KEY`, `DEFAULT_FROM_EMAIL` con el remitente verificado en Brevo, y sin `EMAIL_BACKEND` smtp.

**2026-10-18 - Timeout del SMTP (rama `fix/email-timeout`)**
- En Render el pago con tarjeta se colgaba: la conexión SMTP de la factura nunca respondía (Render free bloquea los puertos SMTP salientes), gunicorn mataba el worker a los 30 s y el navegador mostraba "Failed to fetch" con el pago ya aprobado.
- `EMAIL_TIMEOUT` (5 s por defecto): la conexión falla rápido, `factura.py` registra el error y el pago responde 201.
- La factura no sale desde Render free por SMTP: se resolvió con la API de Brevo (ver la entrada de la US10).

**2026-10-18 - Pago confirmado sin error visible**
- Un error al armar o enviar la factura ya no devuelve 500 en el pago: el callback de `on_commit` es `robust=True`. El pago queda aprobado y la reserva pagada aunque falle la factura (antes el navegador mostraba "Failed to fetch" y, al reintentar, "La reserva ya está pagada").
- Al pagar con éxito, `/pagos/:id` abre un diálogo con los tickets de cada pasajero para descargar el PDF y la línea "Enviando la factura a tu correo…". Ese texto es fijo: el envío de la factura todavía no se verifica desde la pantalla (lo arregla la US10).
- Pendiente de US10: el envío de la factura sigue dentro de la petición; sin `EMAIL_TIMEOUT` un SMTP colgado puede demorar la respuesta.

**2026-10-18 - Revisión de las US06 y US09 e integración real con pagos (rama `fix/sprint2-integracion-reservas`)**
- Pagos trabaja solo con reservas reales: se eliminaron `ReservaDemo`, el endpoint `/api/pagos/reservas/` y la creación de reservas de prueba al abrir "Mis pagos" (en producción permitía pagar reservas inventadas). `pagos.reserva_id` pasa a `ForeignKey`.
- **Migraciones `reservas/0002`** (orden de `Pasaje`, faltaba desde la US09) y **`pagos/0004`** (borra los pagos de prueba de reservas demo, FK y elimina `reservas_demo`). Aplicarlas en Supabase al desplegar.
- El backend exige nombre, apellido y DNI de cada pasajero, uno por pasaje (antes completaba con el titular y DNI "S/D").
- Ida y vuelta: el backend valida que la vuelta haga la ruta inversa y salga después de que llega la ida (misma regla que `vueltasPosibles` del front).
- "Mis reservas" no ofrece pagar una reserva cuyo vuelo se canceló o ya salió. `GET /api/reservas/mias/` se quitó (duplicaba `GET /api/reservas/`).

**2026-10-18 - Reservas de ida y vuelta con pagos separados**
- La selección de ida y vuelta conserva ambos vuelos y muestra un panel de configuración independiente para cada tramo.
- Ida y vuelta pueden tener distinta clase, cantidad y datos de pasajeros; el backend crea una reserva pendiente por tramo dentro de una transacción.
- Si cualquiera de los tramos no se puede reservar con su configuración, no queda creada ninguna de las dos reservas.
- Luego se muestra “Mis reservas”, donde ida y vuelta aparecen como reservas separadas y cada una se paga por separado.
- `POST /api/reservas/ida-vuelta/` recibe configuración propia para cada tramo; pruebas cubren distinta clase/cantidad y rollback ante vuelo de vuelta no disponible.

**2026-10-17 - US10, factura y envío por email**
- Al aprobar una compra, `Pago.numero_factura` recibe un identificador único asociado al pago; no se asigna para pagos rechazados.
- Se genera un PDF con datos del comprador, reserva, vuelo, pasajeros, medio, fecha e importe; se adjunta a un correo HTML/texto dirigido a `contacto_email` de la reserva.
- El email se agenda con `transaction.on_commit()`. Fallos SMTP quedan registrados y no revierten la compra confirmada ni habilitan una segunda compra.
- En local, Django imprime el correo por consola. En producción hay que configurar las credenciales SMTP protegidas en Render antes de verificar el envío real.

**2026-10-17 - US09, ticket electrónico**
- Cada pasaje de una reserva tiene un código individual; el detalle del ticket y su PDF solo están disponibles para el pasajero dueño cuando la reserva está pagada. Un pago pendiente o rechazado no permite visualizarlos ni descargarlos.
- El backend genera bajo demanda un PDF por pasaje con pasajero, vuelo, fechas y horarios, ruta, clase, asiento, código y datos de reserva. La respuesta fuerza la descarga del adjunto.
- Frontend: las reservas confirmadas enlazan al detalle visual de cada ticket y desde allí se descarga el PDF autenticado. El resultado de pago aprobado enlaza a “Mis reservas”.
- `Pasaje` ya relaciona cada ticket con su reserva y conserva los datos del viajero. El orden de los pasajes por código necesitó la migración `reservas/0002`.

**2026-10-17 - US06, reservar pasajes (rama `feat/sprint2-reservas`)**
- App `reservas`: modelos `Reserva` y `Pasaje` con los nombres y constraints de `modelo.dbml` (`reservas`, `pasajes`).
- Endpoints `POST /api/reservas/` y `GET /api/reservas/`, protegidos para rol pasajero.
- Reglas validadas en backend bajo transacción con `select_for_update()` sobre el vuelo: 1 a 9 pasajes, vuelo activo y futuro, y disponibilidad de asientos suficiente en la clase solicitada. Si no hay lugar, se rechaza informando el motivo.
- La reserva persiste temporalmente en `estado = pendiente` y genera un pasaje individual por viajero con su código de pasaje único y precio congelado.
- Integración con `pagos`: `reservas_mock.py` conecta directamente con `Reserva` y `Pasaje`. Al pagar una reserva con tarjeta o Mercado Pago, se confirma la compra y se descuentan los asientos del vuelo en su clase.
- Frontend: `ModalReserva.tsx` abre desde "Tu viaje" tras seleccionar vuelo; pantalla `/reservas` muestra las reservas reales del usuario con estados y enlace directo de pago.
- Migración `reservas/0001_initial`.

**2026-10-15 - US08, confirmar la venta (rama `feat/sprint2-pagos`)**
- Un pago aprobado confirma la compra: la reserva pasa a `pagada` y se descuentan los asientos de cada clase, en una transacción y una sola vez (`servicios.confirmar_compra`, usado por la tarjeta y por Mercado Pago).
- Si al aprobarse un pago ya no se puede vender (reserva ya pagada, vuelo cancelado o que salió, sin asientos), el pago queda rechazado con "corresponde devolución".
- La pantalla de resultado muestra "¡Compra confirmada!" con los pasajes; la reserva, el chip "Confirmada".
- **Migración `pagos/0003`** (`reservas_demo.estado`): marca `pagada` las reservas demo que ya tenían un pago aprobado (no descuenta asientos de esas compras de prueba). En local: `DATABASE_URL= .venv/Scripts/python manage.py migrate`.

**2026-10-15 - US07, pago de pasajes (rama `feat/sprint2-pagos`)**
- App `pagos`: tarjeta simulada y Mercado Pago Checkout Pro (API de Orders, sandbox). Detalle en la sección "Pagos" de arquitectura.md.
- Pantallas: `/reservas` provisoria con 3 reservas demo, `/pagar/:reservaId` (tarjeta con panel de tarjetas de prueba, o MP), `/pagos/:id` (resultado) y "Mis pagos" en el perfil del pasajero.
- Un pago aprobado todavía no descuenta asientos ni marca la reserva como pagada en el modelo: eso es la US08.
- **Migraciones nuevas** (`token_blacklist` de la US23 y `pagos`): con `DATABASE_URL` de Supabase en el `.env`, el login falla con 500 hasta correr `migrate`, porque cada login guarda el token en `token_blacklist_outstandingtoken`. El deploy las aplica solo (`build.sh`); para trabajar local sin tocar Supabase, correr con `DATABASE_URL=` (SQLite).
- `pagos.marca` y `pagos.cuenta_mp` (migración `pagos/0002`). En local: `DATABASE_URL= .venv/Scripts/python manage.py migrate`. El mail y la marca de un pago de MP salen de la orden (`payer.email`, `transactions.payments[0].payment_method.id`); falta confirmarlo con un pago real del sandbox: si MP no los manda, se muestra "Cuenta de Mercado Pago".
- Pago con tarjeta: espera simulada de 2,5 s con el avión como barra (`AvionCargando`).
- **Render:** cargar `MP_ACCESS_TOKEN` y `FRONTEND_URL=https://fly-away-one.vercel.app` antes de probar MP en producción.

**2026-10-15 - Inicio del Sprint 2: US23 y documentación oficial (rama `feat/sprint2-pagos`)**
- US23 (cerrar sesión): el logout ya borraba los tokens del navegador; ahora además invalida el refresh en el servidor con `POST /api/auth/logout/` (`token_blacklist` de SimpleJWT). Un refresh cerrado ya no renueva; los de otros usuarios siguen andando (test en `usuarios/tests.py`). El access vigente vence solo (1 h).
- `README.md` en la raíz como punto de entrada; `arquitectura.md` al día con lo implementado.
- Los specs y planes de trabajo (`docs/superpowers/`) quedan fuera del repo; la documentación oficial es `README.md` + `docs/`.
- `npm audit fix` en el front (vulnerabilidad de `source-map-js`, dependencia de Vite).
- Sprint 2: US06 (reservar) la hace otro integrante; acá siguen US07 (pago) y US08 (confirmar la venta).

**2026-10-03 - Ajustes de interfaz tras probar el ABM (PR #7 y rama `fix/errores-no-json`)**
- Formulario de vuelo al ancho del listado (88rem), con los cuatro campos de cada card en una línea. Listado con paginación centrada: flechas y números (`paginasVisibles` en `lib/adminVuelos.ts`).
- Inicio: el calendario abre hacia arriba cuando abajo no entra (`abreHaciaArriba` en `lib/busqueda.ts`; el alto del calendario está estimado en 380 px en `SelectorFechas`).
- Toda la app: `scrollbar-gutter: stable` (el contenido no salta cuando aparece la barra) y footer con los nombres del equipo, en el layout de `App.tsx`.
- Perfil: muestra el ID del usuario.
- `lib/api.ts`: si el backend responde algo que no es JSON (500 de Django, página de Render), `ApiError` lleva un mensaje fijo en lugar del HTML crudo.
- **Supabase:** migraciones `0002` y `0003` aplicadas por el deploy del PR #6. Se borraron los 6 389 vuelos de ejemplo posteriores al 2026-11-02; quedan 6 960, hasta esa fecha, sobre LV-FAA a LV-FAD. Del 2026-11-03 en adelante no hay vuelos: se cargan desde `/admin/vuelos`. Los aviones LV-FAE a LV-FAJ están libres.

**2026-10-03 - ABM de vuelos, US01, US02 y US03 (rama `feat/abm-vuelos`)**
- `/admin/vuelos`: listado con filtros y paginación, alta con períodos de recurrencia, edición de una instancia (lápiz) y cancelación con confirmación (tacho).
- Backend: `GET/POST /api/vuelos/`, `PATCH /api/vuelos/{id}/`, `POST /api/vuelos/{id}/cancelar/`, `GET /api/aviones/`, todos solo para el rol administrador. Reglas en `vuelos/servicios.py`.
- `vuelos.fecha_llegada` nuevo (vuelos que cruzan medianoche). Las filas existentes quedaron con `fecha_llegada = fecha_operacion`.
- `seed` carga el catálogo y la flota de 10; los vuelos de ejemplo solo con `--vuelos` y ya no corren en `build.sh`.
- Límite actual: cancelar o cambiar el horario no avisa a los pasajeros (US15, US16); no hay reservas todavía.

**2026-10-03 — Revisión de la US22 (rama `feature/autenticacion`)**
- Corregido: las llamadas de autenticación del front duplicaban el prefijo (`/api/api/auth/...`) porque `VITE_API_URL` ya termina en `/api`; ahora usan `/auth/...` como el resto de `lib/`.
- El área del empleado pasa de `/mostrador` a `/empleado`. El rol sigue siendo `empleado_mostrador`.
- Un solo layout con header para los tres roles. Tras iniciar sesión todos llegan a `/`; cambian las opciones del header (`MENU` en `src/lib/auth.ts`): pasajero Vuelos y Reservas; empleado Vuelos y Reservas (`/empleado/reservas`); administrador Vuelos, Reservas (`/admin/reservas`) y Gestión de vuelos (`/admin/vuelos`). Las pantallas nuevas son placeholders; el ABM de vuelos va en `/admin/vuelos`.
- Header con fondo opaco (antes era semitransparente y dejaba ver el hero al hacer scroll).
- Cuentas de prueba creadas en Supabase, una por rol: `admin@gmail.com`, `empleado@gmail.com`, `pepe@gmail.com`. Las contraseñas no se documentan acá; crear los emails siempre en minúsculas (el login distingue mayúsculas).

**2026-10-02 — US22, autenticación de usuarios**
- Backend: login por email con SimpleJWT, registro público exclusivo para pasajeros con validación de contraseña, endpoint autenticado `GET /api/auth/yo/` y cuentas de administrador/empleado gestionables desde Django Admin con contraseña hasheada.
- Frontend: formularios reales de inicio de sesión y registro; recuperación de sesión consultando `/api/auth/yo/`; navegación por rol y guardas para perfil, reservas, administración y mostrador. Empleado no puede abrir administración; pasajero no puede abrir mostrador ni administración. El cierre de sesión elimina ambos tokens.
- Django Admin queda restringido a usuarios activos con rol administrador. Empleados y pasajeros no pueden ingresar; desde allí se crean cuentas de administrador y empleado.
- Pruebas backend cubren creación/autenticación de los tres roles, hash, registro, rol no elevable desde el registro, email duplicado, contraseña débil, credenciales inexistentes/incorrectas sin revelar cuál falló, perfil protegido, usuario inactivo y acceso al admin por rol.
- Límite actual: las áreas de mostrador y administración del frontend siguen siendo placeholders y la búsqueda de vuelos es pública; las nuevas operaciones de negocio deben exigir autenticación y permiso del rol en el backend. Las guardas de frontend solo resuelven navegación, no son una barrera de seguridad.

**2026-10-02 — Calendario de rango y logo de la card (rama `fix/logo-card-y-calendario`)**
- El buscador tiene una caja por tramo: "Fechas" en solo ida; "Ida" y "Vuelta" en ida y vuelta. Cada caja abre un calendario (`SelectorFechas`, con react-day-picker): primer clic = inicio, segundo = fin, el mismo día = un solo día. La lógica de búsqueda, la URL y el backend no cambian.
- La card de resultados usa `logoA`, como el detalle.

**2026-10-02 — Backend de vuelos (rama `feat/backend-vuelos`)**
- Modelo `usuarios` del DBML (login por email, `rol`), que reemplaza a `accounts`.
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
- Vuelos ya conectados al backend (ver arriba).
- Las áreas `/reservas`, `/mostrador` y `/admin` siguen como placeholders, detrás de las guardas de autenticación y rol.
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
| 2026-10-17 | La reserva de pasajes se crea en estado 'pendiente' y genera pasajes con precio congelado | Cumple que la reserva no es compra confirmada y asegura el precio al momento de reservar |
| 2026-10-18 | Se elimina `reservas_demo` y `pagos.reserva_id` pasa a FK; se borran los pagos de prueba | Con reservas reales, las demo dejaban pagar reservas inventadas en producción |
| 2026-10-18 | Ida y vuelta = dos reservas, cada una con su pago | Cada tramo puede tener otra clase y cantidad; `pagos` sigue apuntando a una sola reserva |
| 2026-10-15 | Los asientos se descuentan solo al confirmarse el pago, no al iniciarlo ni al reservar | Cumple "un pago rechazado no modifica definitivamente la disponibilidad" sin retenciones que liberar; si con MP no quedan asientos al aprobarse, se marca para devolución |
| 2026-10-15 | Mastercard acepta el prefijo 50 en la tarjeta simulada | La tarjeta de prueba de MP (5031...) también vale en el formulario propio |
| 2026-10-15 | Antes de otro intento, una orden de MP sin pagar se cancela; una en proceso bloquea (409) | Evita cobrar dos veces la misma reserva |
| 2026-10-15 | Pagos con Mercado Pago Checkout Pro (API de Orders, sandbox) y una pasarela de tarjetas simulada propia | MP es lo real del mercado local; Orders es lo que MP recomienda para integraciones nuevas. La tarjeta simulada anda sin internet ni credenciales (demo y tests). Visa/Mastercard no tienen un mock público para comercios |
| 2026-10-15 | Reservas de pagos en una tabla temporal `reservas_demo` y `pagos.reserva_id` sin FK | La US06 la hace otro integrante; no se pisa su modelo y el contrato queda escrito en arquitectura.md |
| 2026-10-15 | Logout con blacklist del refresh token (SimpleJWT), sin bajar la vida del access | Cumple "la sesión queda invalidada" sin dependencias nuevas; el access dura como mucho 1 h más |
| 2026-10-03 | El lápiz queda habilitado en vuelos cancelados o que ya salieron y abre el formulario en solo lectura | Permite consultar cualquier instancia; el tacho sí se deshabilita |
| 2026-10-03 | Una respuesta del backend que no es JSON se muestra como "No pudimos conectar con el servidor" | La API siempre responde JSON; un texto es una página de error que no hay que volcar en pantalla |
| 2026-10-03 | El backend asigna `numero_vuelo` (uno por alta, `FA ` + correlativo) y no se edita | El identificador de cada instancia es su `id`; evita choques con el índice único. Un alta nueva siempre recibe un número nuevo |
| 2026-10-03 | Un avión y un par de precios por período de recurrencia | Cubre "el o los aviones" y temporadas sin cambiar el esquema: cada fila sigue teniendo un solo avión |
| 2026-10-03 | `fecha_llegada` en `vuelos`, calculada por el backend | Soporta vuelos que cruzan medianoche sin ambigüedad en duración, vueltas posibles y avión libre |
| 2026-10-03 | Se valida que el avión esté libre (sin vuelos activos superpuestos) | Evita programar dos vuelos con el mismo avión; rotación y ubicación quedan fuera |
| 2026-10-03 | Cancelar cambia `estado`; no hay borrado | La US03 pide conservar el historial |
| 2026-10-03 | Misma interfaz para los tres roles: inicio en `/` y header con opciones según el rol, en vez de un panel separado por rol | Menos layouts que mantener; se ve claro que el rol cambia las opciones. Si el ABM queda apretado, `/admin` puede pasar a un layout de panel sin tocar las pantallas |
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

- [ ] **Webhook de Mercado Pago:** hoy el estado se consulta al volver del checkout; con webhook se confirmaría aunque el pasajero cierre la pestaña.
- [ ] **Devoluciones:** un pago aprobado que no pudo confirmar la compra (reserva ya pagada, vuelo cancelado o sin asientos) queda rechazado con "corresponde devolución", pero la devolución no se automatiza.
- [x] **Integrar US06 con pagos:** `reservas_mock.py` sobre `Reserva`/`Pasaje`, FK en `pagos.reserva_id` y `reservas_demo` eliminada (migración `pagos/0004`).
- [x] **¿La reserva retiene asientos al crearse?** Resuelto: los asientos se descuentan únicamente al confirmarse el pago (US08); un pago rechazado no modifica disponibilidad.
- [x] **Proveedor de email en prod:** API de Brevo con `django-anymail` (Render free bloquea el SMTP).
- [ ] **Estado real del envío de la factura:** el diálogo de tickets dice "Enviando la factura a tu correo…" fijo. Propuesta: guardar `pagos.factura_enviada_en` al aceptar Brevo el mail (migración y DBML) y mostrar "Te enviamos la factura a …" o "No pudimos enviar la factura".
- [ ] **Periodo de venta:** el modelo lo toma como "fechas en que opera". Si la cátedra lo entiende como "desde cuándo se puede comprar", falta un campo (ej. `venta_desde`). Confirmar con el docente.
- [x] **Ida y vuelta en la compra:** resuelto, son 2 reservas con un pago cada una.
- [ ] ¿El empleado de mostrador puede cancelar/modificar reservas?
- [ ] **Extender un vuelo existente:** un alta nueva siempre recibe un número nuevo. Si hace falta sumar fechas a un número ya usado, agregar un campo opcional al alta.

## Próximos pasos

1. Reportes de ocupación.
2. Notificaciones por cambio de horario / cancelación (el ABM ya cancela y edita; falta avisar).
