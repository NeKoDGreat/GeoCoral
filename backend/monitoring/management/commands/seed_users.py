"""Create or refresh the shared local-development accounts.

Run after migrations with:
    python manage.py seed_users
"""

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from monitoring.models import UserProfile


USERS = (
    ("cenro_staff", "CENRO Staff", "geocoralcenrostaff", "cenro_staff"),
    (
        "sanctuary_manager",
        "Sanctuary Manager",
        "geocoralsanctuarymanager",
        "sanctuary_manager",
    ),
    ("diver", "Authorized Diver", "geocoraldiver", "diver"),
    ("admin", "Administrator", "geocoraladmin", "admin"),
)


class Command(BaseCommand):
    help = "Create or refresh shared GeoCoral local-development user accounts."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Refusing to create shared accounts because DEBUG is not enabled. "
                "These fixed credentials are for local development only."
            )

        user_model = get_user_model()
        admin_permissions = self._admin_permissions()

        with transaction.atomic():
            for username, label, password, role in USERS:
                user, created = user_model.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": f"{username}@example.invalid",
                    },
                )
                user.email = f"{username}@example.invalid"
                user.is_active = True
                user.is_staff = role == "admin"
                user.is_superuser = False
                user.set_password(password)
                user.save()

                UserProfile.objects.update_or_create(
                    user=user,
                    defaults={"role": role, "phone_number": ""},
                )

                if role == "admin":
                    user.user_permissions.set(admin_permissions)
                else:
                    user.user_permissions.clear()

                status = "Created" if created else "Updated"
                self.stdout.write(f"{status}: {label} ({username})")

        self.stdout.write(self.style.SUCCESS(
            "Shared local-development accounts are ready. "
            "Running this command again resets their passwords to the documented values."
        ))

    @staticmethod
    def _admin_permissions():
        permissions = []
        for model in apps.get_app_config("monitoring").get_models():
            content_type = ContentType.objects.get_for_model(model)
            for action in ("view", "add", "change"):
                permissions.append(Permission.objects.get(
                    content_type=content_type,
                    codename=f"{action}_{model._meta.model_name}",
                ))

        user_model = get_user_model()
        user_content_type = ContentType.objects.get_for_model(user_model)
        permissions.append(Permission.objects.get(
            content_type=user_content_type,
            codename=f"view_{user_model._meta.model_name}",
        ))
        return permissions
