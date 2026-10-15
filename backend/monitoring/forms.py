"""
GeoCoral — public-facing forms.

DiverRegistrationForm is the self-service signup used by
monitoring/templates/registration/register.html. Divers create their own
accounts here, always as the "diver" role (see UserProfile.ROLE_CHOICES
in models.py). CENRO and manager accounts are assigned by an authorized
system operator.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


class DiverRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(required=True, max_length=30)

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


class DiverAccountSettingsForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(required=True, max_length=30)

    class Meta:
        model = User
        fields = ["username", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone_number"].initial = self.instance.profile.phone_number

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = user.profile
            profile.phone_number = self.cleaned_data["phone_number"]
            profile.save(update_fields=["phone_number"])
        return user