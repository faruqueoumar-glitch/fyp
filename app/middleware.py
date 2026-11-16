from .tenancy import reset_current_pharmacy_id, set_current_pharmacy_id
from django.core.cache import cache
from django.http import HttpResponseTooManyRequests
import time


class PharmacyContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        pharmacy_id = request.session.get('pharmacy_id')
        try:
            pharmacy_id = int(pharmacy_id) if pharmacy_id is not None else None
        except (TypeError, ValueError):
            pharmacy_id = None

        request.pharmacy_id = pharmacy_id
        token = set_current_pharmacy_id(pharmacy_id) if pharmacy_id else None
        try:
            request.pharmacy = (
                request.user.pharmacy
                if pharmacy_id and request.user.is_authenticated
                else None
            )
            return self.get_response(request)
        finally:
            if token is not None:
                reset_current_pharmacy_id(token)


class BruteForceRateLimitMiddleware:
    """
    Lightweight rate-limiting middleware protecting /login/, /password-reset/, and /register/
    against brute-force / email-flood abuse.

    Max 10 POST attempts per 5 minutes per IP/path.
    Returns HTTP 429 with a user-friendly message when exceeded.
    """

    PROTECTED_PATHS = {'/login/', '/password-reset/', '/register/'}

    MAX_ATTEMPTS = 10
    WINDOW_SECONDS = 300  # 5 minutes

    def __init__(self, get_response):
        self.get_response = get_response

    def _get_identification(self, request):
        """Create a unique identification string: ip|path"""
        path = request.path
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        return f"{ip}|{path}"

    def _check_rate_limit(self, ident):
        """Check if the identification has exceeded the rate limit."""
        cache_key = f"brute_force_{ident}"
        attempt_count = cache.get(cache_key, 0)
        if attempt_count >= self.MAX_ATTEMPTS:
            return True
        return False

    def _increment_rate_limit(self, ident):
        """Increment the attempt counter for the identification."""
        cache_key = f"brute_force_{ident}"
        current = cache.incr(cache_key)
        if current == 1:
            cache.expire(cache_key, self.WINDOW_SECONDS)
        return current

    def _reset_rate_limit(self, ident):
        """Reset/clear the rate limit counter for identification."""
        cache_key = f"brute_force_{ident}"
        cache.delete(cache_key)

    def __call__(self, request):
        if request.method == 'POST':
            path = request.path
            for protected_prefix in self.PROTECTED_PATHS:
                if path.startswith(protected_prefix):
                    ident = self._get_identification(request)

                    if self._check_rate_limit(ident):
                        self._increment_rate_limit(ident)
                        return HttpResponseTooManyRequests(
                            json.dumps({
                                'error': 'Too many attempts. Please wait before trying again.',
                                'retry_after': 300
                            }),
                            content_type='application/json'
                        )

                    self._increment_rate_limit(ident)
                    break

        response = self.get_response(request)
        if response.status_code == 429:
            response['Cache-Control'] = 'no-store, must-revalidate'
        return response


class IdempotencyMiddleware:
    """
    Idempotency middleware for protecting against duplicate form submissions.

    Works by:
    1. Checking for a hidden _idempotency_key in POST data
    2. If present, checking Django's cache for 60 seconds
    3. If already seen, blocking the duplicate with 409 Conflict
    4. If new, storing the key in cache for 60 seconds
    """

    PROTECTED_PATHS = {'/login/', '/password-reset/', '/register/'}

    def __init__(self, get_response):
        self.get_response = get_response

    def _get_idempotency_key(self, request):
        """Extract idempotency key from POST data."""
        if request.method == 'POST':
            key = request.POST.get('_idempotency_key')
            if key:
                return key
        return None

    def _is_duplicate(self, key):
        """Check if the idempotency key already exists in cache."""
        if not key:
            return False
        cache_key = f"idempotency_{key}"
        return cache.get(cache_key) is not None

    def _mark_processed(self, key, timeout=60):
        """Mark the idempotency key as processed for the given timeout (seconds)."""
        cache_key = f"idempotency_{key}"
        cache.set(cache_key, '1', timeout)

    def __call__(self, request):
        if request.method == 'POST':
            path = request.path
            for protected_prefix in self.PROTECTED_PATHS:
                if path.startswith(protected_prefix):
                    key = self._get_idempotency_key(request)
                    if key:
                        if self._is_duplicate(key):
                            return HttpResponseTooManyRequests(
                                json.dumps({
                                    'error': 'This request has already been processed. Please wait and try again.'
                                }),
                                content_type='application/json'
                            )
                        self._mark_processed(key, timeout=60)
                        break

        response = self.get_response(request)
        return response
