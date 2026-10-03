#!/usr/bin/env bash
# Build command de Render
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
# Catálogo (aeropuertos, flota): no tiene ABM. Los vuelos los carga el administrador.
python manage.py seed
