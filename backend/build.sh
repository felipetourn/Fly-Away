#!/usr/bin/env bash
# Build command de Render
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
# Datos de ejemplo hasta que exista el ABM de vuelos (idempotente). Sacar cuando exista.
python manage.py seed
