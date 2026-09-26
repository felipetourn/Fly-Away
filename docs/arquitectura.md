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
│   └── memoria.md            estado + decisiones + pendientes
├── backend/
│   ├── .venv/                (no se commitea)
│   ├── .env / .env.example
│   ├── requirements.txt
│   ├── build.sh              build command de Render
│   ├── manage.py
│   ├── config/               settings, urls, wsgi
│   └── accounts/             User custom con rol
│   # apps a crear: flights/, bookings/, reports/ (ver abajo)
└── frontend/
    ├── .env.local / .env.example
    ├── vercel.json           rewrite SPA
    └── src/
        ├── lib/api.ts        cliente fetch + JWT
        ├── pages/            pantallas
        └── App.tsx           rutas: / (pasajero), /mostrador, /admin
```

## Roles

| Rol (`User.role`) | Interfaz | Puede |
|---|---|---|
| `passenger` | `/` | buscar vuelos, comprar (≤ 9 pasajes), ver/descargar sus pasajes |
| `counter` | `/mostrador` | vender pasajes a un pasajero en mostrador, consultar reservas |
| `admin` | `/admin` | ABM de vuelos, cancelar, reportes de ocupación |

El Django admin (`/admin/` del backend) queda como herramienta interna, no como la interfaz de administradores.

## Modelo de datos (propuesta)

```
Airport        code (IATA, único), name, city
Flight         number, origin→Airport, destination→Airport,
               departure_time, arrival_time,
               weekdays (lista de 0-6),
               sale_from, sale_to               (periodo disponible para venta)
               economy_seats, first_seats,
               economy_price, first_price,
               status (active | cancelled)
Booking        user→User (comprador), flight→Flight, travel_date, seat_class,
               created_at, status                (una transacción, 1..9 pasajes)
Ticket         booking→Booking, passenger_name, passenger_dni, code (único)
Payment        booking→Booking (1:1), amount, method, last4, status, paid_at
```

- **Ocupación** de un vuelo en una fecha = `Ticket` con `booking.flight = X`, `booking.travel_date = D`, agrupado por clase. Sin tabla de "instancias de vuelo".
  - ponytail: si hace falta cancelar/reprogramar **una fecha puntual** (no el vuelo entero), agregar `FlightDate(flight, date, status, overrides)`.
- **Validaciones de compra** (backend, en `transaction.atomic` + `select_for_update` del `Flight`):
  1. 1 ≤ cantidad ≤ 9
  2. `travel_date` dentro de `sale_from..sale_to` y su día de semana ∈ `weekdays`
  3. vuelo `active` y fecha futura
  4. asientos libres de la clase ≥ cantidad
- **Precio** se copia al `Booking`/`Payment` al momento de la compra (si el admin cambia precios después, no afecta ventas pasadas).

## API (propuesta)

```
POST /api/auth/token/            login → {access, refresh}        ✅ hecho
POST /api/auth/token/refresh/                                      ✅ hecho
GET  /api/health/                                                  ✅ hecho
POST /api/auth/register/         alta de pasajero
GET  /api/airports/
GET  /api/flights/search/?origin=&destination=&date=   vuelos + disponibilidad
CRUD /api/flights/               (admin)
POST /api/flights/{id}/cancel/   (admin) → notifica por email
POST /api/bookings/              compra + pago → emails
GET  /api/bookings/mine/
GET  /api/tickets/{code}/pdf/    descarga pasaje
GET  /api/reports/occupancy/?flight=&date_from=&date_to=   (admin)
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
