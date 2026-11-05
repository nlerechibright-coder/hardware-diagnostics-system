from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .services.roles import ACCOUNT_TYPE_CHOICES


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=False)
    account_type = forms.ChoiceField(
        choices=ACCOUNT_TYPE_CHOICES,
        required=True,
        initial='normal',
        label='Account Type',
    )

    class Meta:
        model = get_user_model()
        fields = ('username', 'email', 'account_type', 'password1', 'password2')

    def clean_account_type(self):
        account_type = self.cleaned_data.get('account_type')
        valid_choices = dict(ACCOUNT_TYPE_CHOICES)
        if account_type not in valid_choices:
            raise forms.ValidationError('Select a valid choice.')
        return account_type

    def save(self, commit=True):
        user = super().save(commit=False)
        account_type = self.cleaned_data.get('account_type')
        if commit:
            user.save()
            profile = getattr(user, 'profile', None)
            if profile is None:
                from .models import UserProfile
                profile = UserProfile.objects.create(user=user)
            profile.account_type = account_type
            profile.save(update_fields=['account_type'])
        return user
