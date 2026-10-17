"""
GeoCoral — template context processors.

Makes the authenticated user's application role and workspace URL
available to the shared navigation template.
"""

from .permissions import get_user_role


def role_flags(request):
    return {
        "user_role": get_user_role(request.user),
        "role_home_url": (
            "monitoring:diver_home"
            if get_user_role(request.user) == "diver"
            else "monitoring:dashboard"
        ),
    }