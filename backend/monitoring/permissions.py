"""
GeoCoral — role-checking helpers.

Divers can submit photos but should not see the management dashboard,
edit/delete other people's records, or verify classifications — those
actions are for CENRO staff, sanctuary managers, and admins (see
UserProfile.ROLE_CHOICES in models.py). Centralized here so the
frontend dashboard access check and the API's write permissions stay
in agreement.
"""

STAFF_ROLES = {"cenro_staff", "sanctuary_manager", "admin"}


def is_staff_role(user):
    """True for CENRO staff / sanctuary managers / admins, and for
    Django superusers (who may not have a UserProfile at all, e.g. the
    account created via createsuperuser)."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.role in STAFF_ROLES)