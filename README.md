# Fly Away

Sistema web de una aerolínea nacional: búsqueda de vuelos, gestión de vuelos por el administrador, venta de pasajes, pagos, emails y reportes de ocupación. Proyecto de Administración de Proyectos de Software 2026.

- Frontend: https://fly-away-one.vercel.app
- Backend: https://fly-away-iz7s.onrender.com/api/health/ (Render free se duerme; la primera llamada tarda ~1 min)

## Documentación

| Documento | Qué tiene |
|---|---|
| [docs/enunciado.md](docs/enunciado.md) | Requisitos de la cátedra y alcance del equipo |
| [docs/arquitectura.md](docs/arquitectura.md) | Stack, carpetas, roles, modelo de datos, API, deploy y cómo correr en local |
| [docs/modelo.dbml](docs/modelo.dbml) | Modelo relacional. **Fuente de verdad del esquema** (se ve en dbdiagram.io) |
| [docs/memoria.md](docs/memoria.md) | Qué está hecho, decisiones tomadas con su motivo y pendientes |
| [docs/US/](docs/US/) | Una ficha por user story y sprint: horas, criterios de aceptación con su evidencia y cómo probarla |

## Correr en local

Requisitos: Python 3.11 y Node 22. Detalle en [arquitectura.md](docs/arquitectura.md#correr-en-local).

```bash
# Backend (desde backend/)
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Linux/Mac: .venv/bin/pip
cp .env.example .env
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py seed --vuelos
.venv/Scripts/python manage.py runserver          # http://localhost:8000
.venv/Scripts/python manage.py test

# Frontend (desde frontend/)
npm install
cp .env.example .env.local
npm run dev      # http://localhost:5173
npm run build    # verifica tipos
npm run lint
npm run check    # chequeos de la lógica pura
```

## Convenciones

- Todo en **español**: código de dominio, textos de UI, docs y commits. Modelos y campos con los mismos nombres que `modelo.dbml`; si cambia el esquema, se actualiza primero ese archivo.
- Una rama por tarea (`feat/...`, `fix/...`) y merge a `main` por pull request. `main` despliega solo en Render y Vercel.
- Commits con prefijo: `feat(backend): ...`, `fix(frontend): ...`, `docs: ...`, `chore: ...`.
- Reglas de negocio (máximo 9 pasajes, capacidad, fechas) se validan en el **backend**; el front solo las repite por UX. Toda operación por rol valida el permiso en su endpoint.
- Compras dentro de `transaction.atomic()` con `select_for_update()` sobre el vuelo.
- Frontend: la API se llama solo desde `src/lib/api.ts`.
- Configuración sensible solo por variables de entorno (`backend/.env`, `frontend/.env.local`); nunca se commitean. Variable nueva: agregarla también al `.env.example`.
- Al cerrar una tarea, actualizar [memoria.md](docs/memoria.md) (estado, decisiones, pendientes).
