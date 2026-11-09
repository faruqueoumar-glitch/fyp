from .tenancy import reset_current_pharmacy_id, set_current_pharmacy_id


class PharmacyContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        pharmacy_id = (
            user.pharmacy_id
            if user is not None and user.is_authenticated
            else None
        )
        request.pharmacy_id = pharmacy_id
        request.pharmacy = getattr(user, 'pharmacy', None) if pharmacy_id else None
        token = set_current_pharmacy_id(pharmacy_id) if pharmacy_id else None
        try:
            return self.get_response(request)
        finally:
            if token is not None:
                reset_current_pharmacy_id(token)
