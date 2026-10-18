# Arquitectura — Fly Away

## Stack

| Capa | Tecnología | Hosting |
|---|---|---|
| Frontend | TypeScript + React 19 + Vite + Tailwind v4 + react-router | Vercel |
| Backend | Python 3.11 + Django 5.2 + Django REST Framework + SimpleJWT | Render (Web Service) |
| Base de datos | PostgreSQL vía Django ORM | Supabase |
| Email | Django `send_mail` (consola en local, SMTP/API en prod) | ver pendientes |

```
[Navegador] ──HTTPS──> [Vercel: SPA React]
     │
     └──fetch JSON + JWT──> [Render: Django /api/*] ──SQL──> [Supabase: Postgres]
                                   │
                                   └──> [Proveedor de email]
```

El front es una SPA estática; toda la lógica de negocio y validación vive en el backend. Autenticación con JWT (`Authorization: Bearer <access>`).

## Estructura de carpetas

```
Fly Away/
├── README.md                 punto de entrada (cómo correr, convenciones)
├── docs/
│   ├── enunciado.md
│   ├── arquitectura.md       este archivo
│   ├── modelo.dbml           modelo relacional (fuente de verdad del esquema)
│   └── memoria.md            estado + decisiones + pendientes
├── backend/
│   ├── .venv/                (no se commitea)
│   ├── .env / .env.example
│   ├── requirements.txt
│   ├── build.sh              build command de Render
│   ├── manage.py
│   ├── config/               settings, urls, wsgi
│   ├── usuarios/             modelo Usuario (tabla usuarios, login por email, rol)
│   ├── vuelos/               aeropuertos, aviones, vuelos; búsqueda, detalle y ABM del administrador; comando seed
│   ├── reservas/             reservas y pasajes (US06); selección de clase, cantidad (1..9), disponibilidad y pasajes
│   └── pagos/                pagos (tarjeta simulada y Mercado Pago)
└── frontend/
    ├── .env.local / .env.example
    ├── vercel.json           rewrite SPA
    └── src/
        ├── lib/              api.ts (fetch + JWT + renovación), sesion.tsx, llamadas a la API y lógica pura
        ├── components/       Header, HeroCarrusel, BuscadorVuelos, FiltroPrecio, CardVuelo, ListaVuelos, DetalleVuelo
        ├── pages/            pantallas (AdminVuelos y AdminVueloForm: ABM de vuelos; Reservas provisoria, Pagar, PagoResultado; Perfil con mis pagos)
        └── App.tsx           rutas: / (todos), /empleado/*, /admin/* (por rol)
```

## Roles

| Rol (`usuarios.rol`) | Opciones del header | Puede |
|---|---|---|
| `pasajero` | Vuelos, Reservas (`/reservas`) | buscar vuelos, comprar (≤ 9 pasajes), ver/descargar sus pasajes |
| `empleado_mostrador` | Vuelos, Reservas (`/empleado/reservas`) | vender pasajes a un pasajero en mostrador, consultar reservas |
| `administrador` | Vuelos, Reservas (`/admin/reservas`), Gestión de vuelos (`/admin/vuelos`) | ABM de vuelos, cancelar, reportes de ocupación |

Todos los roles comparten layout, header y footer y, al iniciar sesión, llegan a `/` (búsqueda de vuelos); el header muestra las opciones del rol (`MENU` en `src/lib/auth.ts`).

El Django admin (`/admin/` del backend) queda como herramienta interna, no como la interfaz de administradores.

## Modelo de datos

**Fuente de verdad: [modelo.dbml](modelo.dbml)** (se visualiza en dbdiagram.io). Si cambia el esquema, se actualiza primero ese archivo.

```
usuarios        (rol: administrador | empleado_mostrador | pasajero)
aeropuertos     catálogo IATA
aviones         capacidad_economy, capacidad_primera
vuelos          una fila por vuelo real en una fecha → avion, origen, destino, creado_por
  └─ reservas   comprador (usuario) + vuelo + cantidad_pasajes (1..9)
       ├─ pasajes   uno por asiento: datos del viajero, clase, precio, codigo_pasaje
       └─ pagos     monto, estado, ultimos_4, numero_factura
notificaciones  usuario + vuelo (cambio de horario / cancelación)
```

Ideas clave del modelo:

- **Sin tabla de recurrencia.** El admin define en el alta uno o más períodos (desde, hasta, días de la semana, avión y precios); el backend genera **una fila en `vuelos` por fecha**, todas con el mismo `numero_vuelo` (lo asigna el backend) y cada una con su `id`. Cada fila es independiente: modificar o cancelar una no afecta a las demás.
- **Llegada:** `fecha_llegada` la calcula el backend; es el día siguiente a `fecha_operacion` cuando `hora_llegada` es menor que `hora_partida`.
- **Avión libre:** un avión no puede tener dos vuelos activos con horarios superpuestos. Se valida en el alta y en la edición; no contempla rotación ni la ubicación del avión.
- **Capacidad:** al generar un vuelo, `asientos_disponibles_*` se inicializa con la `capacidad_*` del avión. Cada compra descuenta.
- **Validaciones de compra** (backend, dentro de `transaction.atomic()` + `select_for_update()` sobre el vuelo):
  1. 1 ≤ `cantidad_pasajes` ≤ 9
  2. vuelo `activo` y `fecha_operacion` futura
  3. `asientos_disponibles_<clase>` ≥ pasajes pedidos de esa clase
- **Precio** se copia a cada `pasaje` al comprar: si el admin cambia el precio del vuelo después, no afecta ventas pasadas.
- **Comprador ≠ viajero:** `reservas.pasajero_id` es quien compra (recibe emails); los datos de cada viajero están en `pasajes`.
- **Ocupación** (reportes) = capacidad del avión − `asientos_disponibles_*`, por vuelo/fecha/clase.
- **Pagos:** nunca guardar el número de tarjeta completo; solo `ultimos_4`. Una reserva puede tener varios pagos (reintentos tras un rechazo).

Traducción a Django (al implementar):

- `usuarios` → modelo de usuario custom (`AUTH_USER_MODEL`); `password_hash` y `activo` se mapean a `password` e `is_active` de Django con `db_column`.
- Enums → `CharField` + `choices` (en la BD quedan como `varchar`).
- `actualizado_en` → `auto_now=True`; `creado_en` → `auto_now_add=True`.
- `db_table` explícito para que las tablas se llamen igual que en el DBML.
- Reglas simples como constraints de Postgres (`CheckConstraint`): cantidad 1..9, origen ≠ destino.

## Contrato entre reservas (US06) y pagos (US07/US08)

Los pagos se implementan antes que las reservas. Para no bloquearse ni pisar la US06, la app `pagos` trabaja con una **tabla temporal propia** y un único punto de contacto:

- **`reservas_demo`** (modelo `ReservaDemo` en `pagos`): `id`, `pasajero`, `vuelo`, `clase`, `cantidad`, `estado` (`pendiente` | `pagada`). Al entrar a `/reservas`, cada pasajero recibe 3 reservas demo fijas (economy × 1, primera × 2, economy × 9) para poder pagar. No es la tabla `reservas` del DBML y ninguna FK la apunta.
- **`pagos.reserva_id`** es un UUID **sin FK** que hoy guarda el id de una reserva demo.
- **`pagos/reservas_mock.py`** es lo único que conoce las reservas. Expone `reservas_de(usuario)`, `pasajes_de(reserva)` (clase y precio por asiento), `monto_de(reserva)` (suma de los precios de los pasajes), `reserva_de_pago(pago)` y `marcar_pagada(reserva)` (US08).

Lo que la US06 tiene que respetar para que pagos funcione sin cambios:

1. `Reserva` y `Pasaje` con los nombres de [modelo.dbml](modelo.dbml) (`reservas`, `pasajes`). La clase y el precio van en cada **pasaje**; el monto a pagar es la **suma de `pasajes.precio`**.
2. Una reserva recién creada queda en `estado = pendiente`. El paso a `pagada` y el descuento de `asientos_disponibles_*` los hace pagos (`confirmar_compra`, US08) cuando el pago se aprueba; la US06 no los toca.
3. A definir con pagos: si la reserva **retiene asientos** al crearse. Hoy los asientos se descuentan **solo al confirmarse el pago**; si la US06 retiene asientos, `confirmar_compra` pasa a convertir la retención en venta en vez de descontar.

Al integrar la US06: se reescribe `reservas_mock.py` sobre `Reserva`/`Pasaje` (misma interfaz), `pagos.reserva_id` pasa a `ForeignKey` a `reservas`, se borran los pagos de prueba de reservas demo y una migración elimina `reservas_demo`. El botón **Pagar** de la pantalla de reservas lleva a `/pagar/:reservaId`.

## API

✅ = implementado. Lo demás es la propuesta para lo que falta.

```
POST /api/auth/token/            login por email → {access, refresh} ✅
POST /api/auth/token/refresh/                                      ✅
POST /api/auth/registro/         alta pública de pasajero            ✅
GET  /api/auth/yo/               usuario autenticado (JWT)            ✅
POST /api/auth/logout/           {refresh} → invalida ese refresh (blacklist) ✅
GET  /api/health/                                                  ✅ hecho
GET  /api/aeropuertos/                                             ✅ hecho
GET  /api/vuelos/buscar/?origen=&destino=&desde=&hasta=&pasajeros=&clase=&precio_min=&precio_max=   ✅ hecho
                                 origen y/o destino (al menos uno), hasta opcional (sin límite de días);
                                 devuelve vuelos activos, con asientos_disponibles_<clase> >= pasajeros,
                                 precio_<clase> dentro del rango, que todavía no salieron, por fecha y hora;
                                 origen/destino anidados (codigo_iata, ciudad…)
GET  /api/vuelos/{id}/           ✅ hecho — detalle (US05): el mismo vuelo de la búsqueda + avion {matricula, modelo};
                                 incluye cancelados (estado = cancelado) en vez de 404
GET  /api/vuelos/                (admin) ✅ listado paginado (50): q (id o número), origen, destino, desde, hasta, estado;
                                 sin desde ni q, desde hoy
POST /api/vuelos/                (admin) ✅ alta: origen, destino, horas y periodos[{desde, hasta, dias, avion, precios}]
                                 → 201 {numero_vuelo, cantidad}; genera una fila por fecha, todo o nada
PATCH /api/vuelos/{id}/          (admin) ✅ edita una instancia activa que no salió (fecha, horas, ruta, avión, precios)
POST /api/vuelos/{id}/cancelar/  (admin) ✅ estado = cancelado; la fila se conserva. Falta notificar por email (US16)
GET  /api/aviones/               (admin) ✅ catálogo para el formulario
GET  /api/pagos/reservas/        (pasajero) ✅ reservas demo del usuario (hasta la US06): vuelo, clase, cantidad, monto, estado
GET  /api/pagos/                 (pasajero) ✅ sus pagos, del más nuevo al más viejo (estado guardado, no consulta a MP)
GET  /api/pagos/{id}/            (pasajero) ✅ un pago; si es de MP y está pendiente, consulta la orden y lo actualiza
POST /api/pagos/tarjeta/         (pasajero) ✅ {reserva_id, numero, titular, vencimiento MM/AA, cvv} → 201 pago (aprobado o rechazado)
POST /api/pagos/mercadopago/     (pasajero) ✅ {reserva_id} → 201 {pago, checkout_url}; 502 si MP no responde
POST /api/reservas/              ✅ hecho — reservar (US06): vuelo, clase, cantidad (1..9), pasajeros
POST /api/reservas/ida-vuelta/   ✅ hecho — {vuelo_ida, vuelo_vuelta, ida:{clase,cantidad_pasajes,pasajeros}, vuelta:{clase,cantidad_pasajes,pasajeros}}; crea ambas reservas pendientes en una transacción
GET /api/reservas/mias/         ✅ hecho — (pasajero) sus reservas reales
GET  /api/pasajes/{codigo}/      ✅ hecho — (pasajero dueño) detalle del ticket, solo si la compra está pagada
GET  /api/pasajes/{codigo}/pdf/  ✅ hecho — descarga ticket PDF, solo si la compra está pagada
GET  /api/reportes/ocupacion/?vuelo=&desde=&hasta=   (admin)
```

El registro público siempre asigna el rol `pasajero` y valida la contraseña con los validadores de Django. Las cuentas de administrador y empleado se provisionan desde Django Admin por un administrador; las contraseñas se ingresan como texto en el formulario y se guardan hasheadas. Solo los usuarios activos con rol `administrador` son staff y acceden a Django Admin; empleados y pasajeros no acceden. El frontend renueva el access token con el refresh al recibir un 401 y descarta la sesión si la renovación falla. Cerrar sesión borra los tokens del navegador y manda el refresh a `/api/auth/logout/`, que lo invalida en el servidor (`token_blacklist` de SimpleJWT): ese refresh ya no renueva, y el access vigente vence solo (1 h). Las sesiones de otros usuarios o dispositivos no se tocan. Las rutas `/admin/*` (React) y `/empleado/*` exigen administrador y empleado, respectivamente (cualquier otro rol vuelve a `/`); las búsquedas públicas de vuelos siguen abiertas. Cualquier nueva operación de negocio exclusiva por rol debe validar el permiso también en su endpoint de backend.

**Errores 400:** formato estándar de DRF, `{"parametro": ["mensaje"]}`, con mensajes en español (los mismos que muestra el front). Los errores de un período del alta llegan en `periodos` indexados por posición (`{"periodos": {"0": {"desde": ["mensaje"]}}}`); los que no son de un campo, en `non_field_errors`. Un parámetro vacío (`?hasta=`) cuenta como no enviado. El 404 es `{"detail": "..."}`. Si la respuesta no es JSON (error 500, hosting caído), el front muestra un mensaje fijo (`ApiError` en `src/lib/api.ts`).

**Catálogo y datos de ejemplo:** `python manage.py seed` carga los aeropuertos, la flota (10 aviones) y el usuario `sistema`; corre en `build.sh` porque no tienen ABM. `python manage.py seed --vuelos [--dias 60]` agrega vuelos de ejemplo sobre los primeros 4 aviones, para desarrollo local. Es idempotente y no pisa lo existente.

## Pagos

Dos medios. Ninguno guarda el número completo de la tarjeta ni el CVV: solo `ultimos_4`. Cada pago guarda además `marca` (visa, mastercard o amex: la de la tarjeta o la usada dentro de MP) y, si pagó con MP, `cuenta_mp` (el mail del comprador, tomado de la orden). Con eso "Mis pagos" del perfil muestra logo, tarjeta o cuenta, fecha, vuelo, valor y estado.

- **Tarjeta simulada** (`pagos/tarjeta.py`): valida como una pasarela real (Luhn, Visa/Mastercard/Amex, vencimiento, CVV de 3 o 4 dígitos) y decide el resultado por el número. Tarjetas de prueba, una Visa y una Mastercard por caso (también en el botón "Tarjetas de prueba" de la pantalla de pago): aprobada `4242 4242 4242 4242` o `5555 5555 5555 4444`; rechazada por el emisor `4000 0000 0000 0002` o `5200 0000 0000 0007`; fondos insuficientes `4000 0000 0000 9995` o `5200 0000 0000 9990`; error de procesamiento `4000 0000 0000 0119` o `5200 0000 0000 0114`. Cualquier otra válida se aprueba (incluida la Mastercard de prueba de MP, que empieza con 50).
- **Mercado Pago Checkout Pro** con la API de Orders (`pagos/mercadopago.py`, HTTP con urllib): se crea el pago pendiente, se pide la orden (`POST /v1/orders`, `external_reference` y `X-Idempotency-Key` = id del pago, vence en 30 min) y el pasajero va al `checkout_url`. MP lo devuelve a `FRONTEND_URL/pagos/{id}` y el backend consulta la orden (`GET /v1/orders/{id}`); nunca usa los parámetros de la URL de retorno. Sin webhook: un pendiente se actualiza al abrir su detalle o al intentar pagar de nuevo.
- **Confirmación de la venta (US08):** `servicios.confirmar_compra` es el único camino a un pago `aprobado`. Compra confirmada = pago `aprobado` + reserva `pagada` + asientos descontados, en una transacción: bloquea el vuelo y después el pago (siempre en ese orden), relee la reserva y descuenta por clase de pasaje dentro de un savepoint, así nunca queda una venta a medias. **Los asientos se descuentan solo al confirmar**; un rechazo no toca la disponibilidad. Si al aprobarse ya no se puede vender, el pago queda rechazado con "corresponde devolución": reserva ya pagada, vuelo cancelado o que salió, o sin asientos (puede pasar con MP, entre crear la orden y que se apruebe). Una misma transacción no confirma dos veces: si el pago ya no está pendiente, no hace nada.
- **Ticket electrónico (US09):** cada `Pasaje` tiene un `codigo_pasaje` individual. Su detalle y PDF se habilitan solo si `reserva.estado = pagada` y para el pasajero dueño; el PDF se genera bajo demanda y se descarga como adjunto. Las compras pendientes o rechazadas no exponen tickets.
- **Factura (US10):** al confirmar la compra, se asigna un `pagos.numero_factura` único y se agenda el envío para después del commit. El PDF incluye datos del pago, vuelo, reserva y pasajeros; se envía como adjunto a `reservas.contacto_email` (o al email de la cuenta en reservas demo). Un error de SMTP se registra sin revertir la compra ni abrir otro intento aprobado.
- **Una reserva, un solo pago aprobado:** constraint parcial en `pagos` (`pago_un_aprobado_por_reserva`). Antes de un nuevo intento, una orden de MP sin pagar se cancela y una en proceso responde 409.
- **Transacciones:** las llamadas a MP nunca van dentro de `transaction.atomic()`; el pago pendiente se commitea antes, así una falla de MP lo deja rechazado en vez de perderlo.
- **Variables:** `MP_ACCESS_TOKEN` (Access Token de prueba de la app en developers.mercadopago.com; vacío = MP deshabilitado) y `FRONTEND_URL`. En Render: `FRONTEND_URL=https://fly-away-one.vercel.app`.
- **Sandbox:** para pagar en MP se inicia sesión con el comprador de prueba (sus datos se comparten por fuera del repo) y se usa la Mastercard `5031 7557 3453 0604`, CVV `123`, vencimiento `11/30`, titular `APRO` (aprobada) u `OTHE` (rechazada).

## Emails

- Factura de compra: enviada después de confirmar el pago; incluye plantilla HTML y texto, con el comprobante PDF adjunto. Solo se asigna número y se envía para pagos aprobados.
- Local: `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` (predeterminado) → se imprimen en la terminal de `runserver`.
- Producción: configurar `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` y `DEFAULT_FROM_EMAIL` en el entorno de Render. Las credenciales no se guardan en el repositorio.
- Cambio de horario y cancelación: email pendiente de implementar (US15/US16).

## Correr en local

Requisitos: Python 3.11, Node 22.

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/activate            # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env              # completar SECRET_KEY; DATABASE_URL vacío = SQLite local
python manage.py migrate
python manage.py seed             # catálogo; con --vuelos, también vuelos de ejemplo
python manage.py runserver        # http://localhost:8000

# Frontend (otra terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev                       # http://localhost:5173
```

Si `backend/.env` tiene el `DATABASE_URL` de Supabase, los comandos de arriba trabajan sobre la base compartida. Para no tocarla, correrlos con `DATABASE_URL=` vacío (SQLite).

## Deploy

### Supabase (BD)
1. Crear proyecto → Project Settings → Database → **Connection string (URI)**.
2. Usar la del **Session pooler** (puerto 5432, IPv4). La conexión directa es solo IPv6 y Render no la alcanza.
3. Pegarla como `DATABASE_URL` en Render (y en `backend/.env` si querés trabajar local contra Supabase).

### Render (backend)
- New → Web Service → repo, **Root Directory:** `backend`
- Build command: `bash build.sh`
- Start command: `gunicorn config.wsgi:application`
- Env vars: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=<app>.onrender.com`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS=https://<app>.vercel.app`, `CSRF_TRUSTED_ORIGINS=https://<app>.onrender.com`, `PYTHON_VERSION=3.11.9`, variables de email, `MP_ACCESS_TOKEN`, `FRONTEND_URL=https://<app>.vercel.app`.
- Health check path: `/api/health/`

### Vercel (frontend)
- Import repo, **Root Directory:** `frontend`, framework Vite (autodetectado).
- Env var: `VITE_API_URL=https://<app>.onrender.com/api`
