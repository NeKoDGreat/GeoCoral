from django.conf import settings
from django.db import migrations, models


def demote_legacy_admin_accounts(apps, schema_editor):
    UserProfile = apps.get_model("monitoring", "UserProfile")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    database = schema_editor.connection.alias
    profile_rows = UserProfile.objects.using(database).filter(role="admin")
    user_ids = list(profile_rows.values_list("user_id", flat=True))

    profile_rows.update(role="diver")
    for user in User.objects.using(database).filter(pk__in=user_ids):
        if user.is_superuser:
            continue
        user.is_staff = False
        user.save(update_fields=["is_staff"], using=database)
        user.user_permissions.clear()


class Migration(migrations.Migration):
    dependencies = [
        ("monitoring", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(demote_legacy_admin_accounts, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="userprofile",
            name="role",
            field=models.CharField(
                choices=[
                    ("cenro_staff", "CENRO Staff"),
                    ("sanctuary_manager", "Sanctuary Manager"),
                    ("diver", "Authorized Diver"),
                ],
                default="diver",
                max_length=20,
            ),
        ),
    ]
