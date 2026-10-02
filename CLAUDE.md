# Fly Away — guía para Claude

Sistema web de una aerolínea nacional: gestión de vuelos, venta de pasajes, pagos, emails y reportes de ocupación.
Idioma del proyecto: **español** (docs, commits, textos de UI). Modelos y campos con los mismos nombres que [docs/modelo.dbml](docs/modelo.dbml).

## Leer antes de trabajar
- [docs/arquitectura.md](docs/arquitectura.md) — stack, estructura, modelo de datos, API, deploy.
- [docs/modelo.dbml](docs/modelo.dbml) — modelo relacional, **fuente de verdad del esquema**.
- [docs/memoria.md](docs/memoria.md) — estado actual, decisiones tomadas y pendientes. **Actualizarlo al terminar cada tarea.**
- [docs/enunciado.md](docs/enunciado.md) — requisitos originales de la cátedra.

## Estructura
```
backend/    Django 5.2 + DRF + SimpleJWT (Python 3.11, venv en backend/.venv)
frontend/   React 19 + TypeScript + Vite + Tailwind v4 + react-router
docs/       documentación del proyecto
```

## Comandos
```bash
# Backend (desde backend/)
.venv/Scripts/python manage.py runserver          # http://localhost:8000
.venv/Scripts/python manage.py makemigrations
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py test
.venv/Scripts/python manage.py createsuperuser

# Frontend (desde frontend/)
npm run dev      # http://localhost:5173
npm run build    # tsc + vite build (usar para verificar tipos)
npm run lint
npm run check    # chequeos de la lógica pura (scripts/check.ts)
```

## Reglas
- Config sensible solo por variables de entorno (`backend/.env`, `frontend/.env.local`). Nunca commitear `.env`.
  Si se agrega una variable nueva, agregarla también al `.env.example` correspondiente.
- Usuario: hoy existe `accounts.User` provisorio del setup; se reemplaza por el modelo `usuarios` del DBML (rol `administrador` | `empleado_mostrador` | `pasajero`). Referenciarlo siempre con `settings.AUTH_USER_MODEL` / `get_user_model()`.
- Implementar solo lo que se pide. Si el usuario comparte un diseño o pregunta si algo está bien, responder con análisis, sin escribir código.
- Reglas de negocio (máx. 9 pasajes, capacidad, fechas de venta) se validan en el **backend**; el front solo repite la validación por UX.
- Operaciones de compra dentro de `transaction.atomic()` con `select_for_update()` para no sobrevender asientos.
- Frontend: llamar a la API solo vía `src/lib/api.ts`. URL base en `VITE_API_URL`.
- Hacer cambios mínimos; no agregar dependencias sin motivo claro.
