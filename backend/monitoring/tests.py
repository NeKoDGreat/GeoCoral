from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Sanctuary, UserProfile
from .permissions import can_manage_record, get_user_role


class RolePermissionTests(TestCase):
    def setUp(self):
        self.cenro = User.objects.create_user(username="cenro")
        UserProfile.objects.create(user=self.cenro, role="cenro_staff")
        self.manager = User.objects.create_user(username="manager")
        self.manager_profile = UserProfile.objects.create(
            user=self.manager, role="sanctuary_manager"
        )
        self.diver = User.objects.create_user(
            username="diver",
            password="Initial-Password-483!",
        )
        UserProfile.objects.create(user=self.diver, role="diver")
        self.assigned = Sanctuary.objects.create(name="Assigned", area_code="ASG")
        self.other = Sanctuary.objects.create(name="Other", area_code="OTH")
        self.manager_profile.assigned_sanctuaries.add(self.assigned)

    def test_role_home_roles_are_distinct(self):
        self.assertEqual(get_user_role(self.cenro), "cenro_staff")
        self.assertEqual(get_user_role(self.manager), "sanctuary_manager")
        self.assertEqual(get_user_role(self.diver), "diver")

    def test_cenro_can_manage_any_sanctuary(self):
        self.assertTrue(can_manage_record(self.cenro, SimpleNamespace(sanctuary_id=self.other.pk)))

    def test_manager_can_manage_only_assigned_sanctuaries(self):
        self.assertTrue(can_manage_record(
            self.manager, SimpleNamespace(sanctuary_id=self.assigned.pk)
        ))
        self.assertFalse(can_manage_record(
            self.manager, SimpleNamespace(sanctuary_id=self.other.pk)
        ))

    def test_diver_cannot_manage_records(self):
        self.assertFalse(can_manage_record(
            self.diver, SimpleNamespace(sanctuary_id=self.assigned.pk)
        ))

    def test_admin_is_not_an_application_role(self):
        legacy_admin = User.objects.create_user(username="legacy-admin")
        UserProfile.objects.create(user=legacy_admin, role="admin")
        self.assertIsNone(get_user_role(legacy_admin))
        self.assertFalse(can_manage_record(
            legacy_admin, SimpleNamespace(sanctuary_id=self.assigned.pk)
        ))

    def test_role_home_redirects_to_role_specific_workspace(self):
        self.client.force_login(self.cenro)
        self.assertRedirects(
            self.client.get(reverse("monitoring:role_home")),
            reverse("monitoring:dashboard"),
        )

        self.client.force_login(self.manager)
        self.assertRedirects(
            self.client.get(reverse("monitoring:role_home")),
            reverse("monitoring:dashboard"),
        )

        self.client.force_login(self.diver)
        self.assertRedirects(
            self.client.get(reverse("monitoring:role_home")),
            reverse("monitoring:diver_home"),
        )

    def test_guest_landing_page_and_authenticated_role_redirect(self):
        response = self.client.get(reverse("monitoring:landing"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "monitoring/landing.html")

        self.client.force_login(self.diver)
        self.assertRedirects(
            self.client.get(reverse("monitoring:landing")),
            reverse("monitoring:diver_home"),
        )

    def test_map_requires_login_and_renders_for_authenticated_users(self):
        map_url = reverse("monitoring:map")
        response = self.client.get(map_url)
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={map_url}",
        )

        self.client.force_login(self.diver)
        response = self.client.get(map_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "monitoring/map.html")

    def test_role_workspaces_render_separate_templates(self):
        self.client.force_login(self.cenro)
        response = self.client.get(reverse("monitoring:dashboard"))
        self.assertTemplateUsed(response, "monitoring/roles/cenro/dashboard.html")

        self.client.force_login(self.manager)
        response = self.client.get(reverse("monitoring:dashboard"))
        self.assertTemplateUsed(
            response, "monitoring/roles/sanctuary_manager/dashboard.html"
        )

        self.client.force_login(self.diver)
        response = self.client.get(reverse("monitoring:diver_home"))
        self.assertTemplateUsed(response, "monitoring/roles/diver/home.html")

    def test_diver_can_update_account_settings(self):
        self.client.force_login(self.diver)
        settings_url = reverse("monitoring:settings")

        response = self.client.get(settings_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "monitoring/roles/diver/settings.html")

        response = self.client.post(settings_url, {
            "action": "phone",
            "phone_number": "+639171234567",
        })
        self.assertRedirects(response, settings_url)

        self.diver.profile.refresh_from_db()
        self.assertEqual(self.diver.profile.phone_number, "+639171234567")
        self.assertEqual(self.diver.username, "diver")
        self.assertEqual(self.diver.email, "")

        response = self.client.post(settings_url, {
            "action": "password",
            "old_password": "Initial-Password-483!",
            "new_password1": "New-Secure-Password-920!",
            "new_password2": "New-Secure-Password-920!",
        })
        self.assertRedirects(response, settings_url)
        self.diver.refresh_from_db()
        self.assertTrue(self.diver.check_password("New-Secure-Password-920!"))

    def test_diver_password_change_requires_current_password(self):
        self.client.force_login(self.diver)
        response = self.client.post(reverse("monitoring:settings"), {
            "action": "password",
            "old_password": "incorrect",
            "new_password1": "New-Secure-Password-920!",
            "new_password2": "New-Secure-Password-920!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your old password was entered incorrectly")
        self.diver.refresh_from_db()
        self.assertTrue(self.diver.check_password("Initial-Password-483!"))

    def test_account_settings_are_available_to_staff_roles(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("monitoring:settings"))
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse("monitoring:settings"), {
            "action": "phone",
            "phone_number": "+639171234567",
        })
        self.assertRedirects(response, reverse("monitoring:settings"))
        self.manager.profile.refresh_from_db()
        self.assertEqual(self.manager.profile.phone_number, "+639171234567")
