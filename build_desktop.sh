#!/usr/bin/env bash
set -e
export DJANGO_SETTINGS_MODULE=src.settings.dev
export PYTHONPATH="$(pwd):$(pwd)/src"
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/pyinstaller --clean --noconfirm PharmaAuditOS.spec
echo "Desktop build ready at: dist/PharmaAuditOS/PharmaAuditOS"
