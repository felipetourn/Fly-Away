# Fly Away ✈️

Sistema web de gestión de vuelos y venta de pasajes para una aerolínea nacional.

- Enunciado: [docs/enunciado.md](docs/enunciado.md)
- Arquitectura: [docs/arquitectura.md](docs/arquitectura.md)

## Correr en local

Requisitos: Python 3.11, Node 22.

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/activate            # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env              # y completar SECRET_KEY
python manage.py migrate
python manage.py runserver        # http://localhost:8000

# Frontend (otra terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev                       # http://localhost:5173
```
