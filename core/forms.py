# core/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Role


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=Role.choices,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    manager = forms.ModelChoiceField(
        queryset=User.objects.filter(role=Role.MANAGER),
        required=False,
        help_text="Assign a manager if you are registering an Agent.",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "phone",
            "role",
            "manager",
            "password1",
            "password2",
        ]

    def clean(self):
        """Extra validation logic."""
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        manager = cleaned_data.get("manager")

        # If role is agent, manager must be chosen
        if role == Role.AGENT and not manager:
            self.add_error("manager", "Agents must be assigned to a manager.")

        # Managers and Admins cannot have managers
        if role in [Role.MANAGER, Role.ADMIN] and manager:
            self.add_error("manager", "Only Agents can be assigned a manager.")

        return cleaned_data
