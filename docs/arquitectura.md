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
│   └── accounts/             User custom provisorio del setup (se reemplaza por `usuarios`)
│   # apps a crear según modelo.dbml
└── frontend/
    ├── .env.local / .env.example
    ├── vercel.json           rewrite SPA
    └── src/
        ├── lib/              api.ts (fetch + JWT), mocks con la forma de la API, lógica pura
        ├── components/       Header, HeroCarrusel, BuscadorVuelos, CardVuelo, ListaVuelos
        ├── pages/            pantallas
        └── App.tsx           rutas: / (pasajero), /mostrador, /admin
```

## Roles

| Rol (`usuarios.rol`) | Interfaz | Puede |
|---|---|---|
| `pasajero` | `/` | buscar vuelos, comprar (≤ 9 pasajes), ver/descargar sus pasajes |
| `empleado_mostrador` | `/mostrador` | vender pasajes a un pasajero en mostrador, consultar reservas |
| `administrador` | `/admin` | ABM de vuelos, cancelar, reportes de ocupación |

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

- **Sin tabla de recurrencia.** El admin define días de semana + período en el front; el backend genera **una fila en `vuelos` por fecha**. Cada fila es independiente: modificar o cancelar una no afecta a las demás.
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
POST /api/auth/token/            login → {access, refresh}        ✅ hecho
POST /api/auth/token/refresh/                                      ✅ hecho
GET  /api/health/                                                  ✅ hecho
POST /api/auth/registro/         alta de pasajero
GET  /api/auth/yo/               usuario logueado {id, email, nombre, apellido, rol} (header del front)
GET  /api/aeropuertos/
GET  /api/vuelos/buscar/?origen=&destino=&desde=&hasta=&pasajeros=&clase=&precio_min=&precio_max=
                                 origen y/o destino (al menos uno), hasta opcional (rango ≤ 14 días);
                                 devuelve vuelos activos, con asientos_disponibles_<clase> >= pasajeros,
                                 precio_<clase> dentro del rango, que todavía no salieron, por fecha y hora;
                                 origen/destino anidados (codigo_iata, ciudad…)
CRUD /api/vuelos/                (admin) — el alta con días + período genera N filas
POST /api/vuelos/{id}/cancelar/  (admin) → notifica por email
POST /api/reservas/              compra + pago → emails con pasajes y factura
GET  /api/reservas/mias/
GET  /api/pasajes/{codigo}/pdf/  descarga ticket electrónico
GET  /api/reportes/ocupacion/?vuelo=&desde=&hasta=   (admin)
```

## Emails

- Disparados desde el backend: compra confirmada (pasajes + factura), cambio de horario, cancelación.
- Local: `EMAIL_BACKEND=console` → se imprimen en la terminal de `runserver`.
- Prod: SMTP o API HTTP del proveedor (ver pendiente en memoria.md).

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
