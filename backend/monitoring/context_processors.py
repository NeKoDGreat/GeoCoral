"""
GeoCoral — template context processors.

Makes is_staff_role(request.user) available as {{ user_is_staff_role }}
in every template (registered in settings.py TEMPLATES), so base.html
can conditionally show the Dashboard nav link without every view having
to pass this explicitly.
"""

from .permissions import is_staff_role


def role_flags(request):
    return {"user_is_staff_role": is_staff_role(request.user)}