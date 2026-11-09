from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Optional

from django.core.exceptions import ValidationError


_current_pharmacy_id: ContextVar[Optional[int]] = ContextVar(
    'current_pharmacy_id', default=None
)


def get_current_pharmacy_id():
    return _current_pharmacy_id.get()


def set_current_pharmacy_id(pharmacy_id):
    if pharmacy_id is None:
        raise ValidationError('A pharmacy is required for tenant-scoped operations.')
    return _current_pharmacy_id.set(pharmacy_id)


def reset_current_pharmacy_id(token: Token):
    _current_pharmacy_id.reset(token)


@contextmanager
def pharmacy_context(pharmacy_id):
    token = set_current_pharmacy_id(pharmacy_id)
    try:
        yield
    finally:
        reset_current_pharmacy_id(token)


@contextmanager
def without_pharmacy_context():
    token = _current_pharmacy_id.set(None)
    try:
        yield
    finally:
        reset_current_pharmacy_id(token)
