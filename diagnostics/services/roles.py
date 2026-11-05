from django.apps import apps
from rest_framework.permissions import BasePermission

ACCOUNT_TYPE_CHOICES = [
    ("normal", "Normal User"),
    ("technician", "Technician"),
]


def get_account_type(user):
    if not user or not getattr(user, "is_authenticated", False):
        return "normal"

    UserProfile = apps.get_model("diagnostics", "UserProfile")
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"account_type": "normal"},
    )
    if profile.account_type not in dict(ACCOUNT_TYPE_CHOICES):
        profile.account_type = "normal"
        profile.save(update_fields=["account_type"])
    return profile.account_type


def is_technician(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return get_account_type(user) == "technician"


def get_role_name(user):
    if not user or not getattr(user, "is_authenticated", False):
        return "Normal User"
    return "Technician" if get_account_type(user) == "technician" else "Normal User"


class IsTechnician(BasePermission):
    message = "Technician access is required for this resource."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return is_technician(user) or bool(getattr(user, "is_staff", False)) or bool(getattr(user, "is_superuser", False))