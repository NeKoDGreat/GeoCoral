"""
GeoCoral — role-checking helpers.

Divers can submit photos but should not see the management dashboard,
edit/delete other people's records, or verify classifications — those
actions are for CENRO staff and sanctuary managers (see
UserProfile.ROLE_CHOICES in models.py). Centralized here so the
frontend dashboard access check and the API's write permissions stay
in agreement.
"""

STAFF_ROLES = {"cenro_staff", "sanctuary_manager"}


def get_user_role(user):
    """Return an application role, treating technical Django superusers as CENRO."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return "cenro_staff"
    profile = getattr(user, "profile", None)
    role = profile.role if profile else None
    return role if role in STAFF_ROLES | {"diver"} else None


def is_staff_role(user):
    """True for CENRO staff, sanctuary managers, and technical superusers."""
    return get_user_role(user) in STAFF_ROLES


def can_manage_record(user, record):
    """CENRO can manage all records; managers can manage assigned sanctuaries."""
    role = get_user_role(user)
    if role == "cenro_staff":
        return True
    if role != "sanctuary_manager":
        return False
    return user.profile.assigned_sanctuaries.filter(
        pk=record.sanctuary_id
    ).exists()