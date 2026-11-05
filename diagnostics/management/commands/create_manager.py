from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from diagnostics.models import UserProfile

class Command(BaseCommand):
    help = 'Creates or resets the Hardware manager account'

    def handle(self, *args, **kwargs):
        username = 'Hardware'
        password = 'MennyWizzy2026!'
        
        # Delete existing to ensure clean state
        User.objects.filter(username=username).delete()
        self.stdout.write(self.style.WARNING(f'Deleted existing {username} user.'))
        
        # Create fresh user
        user = User.objects.create_user(
            username=username, 
            password=password, 
            is_staff=True, 
            is_active=True,
            email='admin@hardware.local'
        )
        UserProfile.objects.get_or_create(user=user, defaults={'account_type': 'technician'})
        
        self.stdout.write(self.style.SUCCESS(f'✅ Successfully created manager: {username}'))
        self.stdout.write(f'   is_staff: {user.is_staff}')
        self.stdout.write(f'   is_active: {user.is_active}')
