#!/usr/bin/env bash
set -e
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/pyinstaller --clean --noconfirm PharmaAuditOS.spec
echo "Desktop build ready at: dist/PharmaAuditOS/PharmaAuditOS"
