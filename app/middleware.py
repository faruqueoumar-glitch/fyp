from .tenancy import reset_current_pharmacy_id, set_current_pharmacy_id


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
