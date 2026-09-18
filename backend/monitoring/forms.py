"""
GeoCoral — public-facing forms.

DiverRegistrationForm is the self-service signup used by
monitoring/templates/registration/register.html. It's intentionally
separate from anything in the Django admin: divers create their own
accounts here, always as the "diver" role (see UserProfile.ROLE_CHOICES
in models.py) — promoting someone to CENRO staff or sanctuary manager
stays an admin-only action, done through /admin/.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


class DiverRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=False)
    phone_number = forms.CharField(required=False, max_length=30)

    class Meta:
        model = User
        fields = ["username", "email", "phone_number", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            UserProfile.objects.create(
                user=user,
                role="diver",
                phone_number=self.cleaned_data.get("phone_number", ""),
            )
        return user