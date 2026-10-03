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
├── CLAUDE.md                 guía para Claude (comandos, reglas)
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
│   └── vuelos/               aeropuertos, aviones, vuelos; búsqueda, detalle y ABM del administrador; comando seed
└── frontend/
    ├── .env.local / .env.example
    ├── vercel.json           rewrite SPA
    └── src/
        ├── lib/              api.ts (fetch + JWT), llamadas a la API, lógica pura (sesión todavía mock)
        ├── components/       Header, HeroCarrusel, BuscadorVuelos, FiltroPrecio, CardVuelo, ListaVuelos, DetalleVuelo
        ├── pages/            pantallas (AdminVuelos y AdminVueloForm: ABM de vuelos)
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

## API (propuesta)

```
POST /api/auth/token/            login por email → {access, refresh} ✅
POST /api/auth/token/refresh/                                      ✅
POST /api/auth/registro/         alta pública de pasajero            ✅
GET  /api/auth/yo/               usuario autenticado (JWT)            ✅
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
POST /api/reservas/              compra + pago → emails con pasajes y factura
GET  /api/reservas/mias/
GET  /api/pasajes/{codigo}/pdf/  descarga ticket electrónico
GET  /api/reportes/ocupacion/?vuelo=&desde=&hasta=   (admin)
```

El registro público siempre asigna el rol `pasajero` y valida la contraseña con los validadores de Django. Las cuentas de administrador y empleado se provisionan desde Django Admin por un administrador; las contraseñas se ingresan como texto en el formulario y se guardan hasheadas. Solo los usuarios activos con rol `administrador` son staff y acceden a Django Admin; empleados y pasajeros no acceden. El frontend renueva el access token con el refresh al recibir un 401 y descarta la sesión si la renovación falla. Las rutas `/admin/*` (React) y `/empleado/*` exigen administrador y empleado, respectivamente (cualquier otro rol vuelve a `/`); las búsquedas públicas de vuelos siguen abiertas. Cualquier nueva operación de negocio exclusiva por rol debe validar el permiso también en su endpoint de backend.

**Errores 400:** formato estándar de DRF, `{"parametro": ["mensaje"]}`, con mensajes en español (los mismos que muestra el front). Los errores de un período del alta llegan en `periodos` indexados por posición (`{"periodos": {"0": {"desde": ["mensaje"]}}}`); los que no son de un campo, en `non_field_errors`. Un parámetro vacío (`?hasta=`) cuenta como no enviado. El 404 es `{"detail": "..."}`. Si la respuesta no es JSON (error 500, hosting caído), el front muestra un mensaje fijo (`ApiError` en `src/lib/api.ts`).

**Catálogo y datos de ejemplo:** `python manage.py seed` carga los aeropuertos, la flota (10 aviones) y el usuario `sistema`; corre en `build.sh` porque no tienen ABM. `python manage.py seed --vuelos [--dias 60]` agrega vuelos de ejemplo sobre los primeros 4 aviones, para desarrollo local. Es idempotente y no pisa lo existente.

## Emails

- Disparados desde el backend: compra confirmada (pasajes + factura), cambio de horario, cancelación.
- Local: `EMAIL_BACKEND=console` → se imprimen en la terminal de `runserver`.
- Prod: SMTP o API HTTP del proveedor (ver pendiente en memoria.md).

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
- Env vars: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=<app>.onrender.com`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS=https://<app>.vercel.app`, `CSRF_TRUSTED_ORIGINS=https://<app>.onrender.com`, `PYTHON_VERSION=3.11.9`, variables de email.
- Health check path: `/api/health/`

### Vercel (frontend)
- Import repo, **Root Directory:** `frontend`, framework Vite (autodetectado).
- Env var: `VITE_API_URL=https://<app>.onrender.com/api`
