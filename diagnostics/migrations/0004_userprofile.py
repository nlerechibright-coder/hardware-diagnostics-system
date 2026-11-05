from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_legacy_technician_accounts(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('diagnostics', 'UserProfile')
    Group = apps.get_model('auth', 'Group')

    technician_group = Group.objects.filter(name='Technician').first()
    if not technician_group:
        technician_group = Group.objects.filter(name='Technician').first()

    if technician_group:
        for user in User.objects.filter(groups=technician_group):
            profile, _ = UserProfile.objects.get_or_create(user_id=user.pk)
            profile.account_type = 'technician'
            profile.save(update_fields=['account_type'])

    for user in User.objects.exclude(pk__in=UserProfile.objects.values_list('user_id', flat=True)):
        profile, _ = UserProfile.objects.get_or_create(user_id=user.pk)
        profile.account_type = 'normal'
        profile.save(update_fields=['account_type'])


def reverse_migrate_legacy_technician_accounts(apps, schema_editor):
    UserProfile = apps.get_model('diagnostics', 'UserProfile')
    UserProfile.objects.filter(account_type='technician').update(account_type='normal')


class Migration(migrations.Migration):

    dependencies = [
        ('diagnostics', '0003_diagnosticrule_role_guidance'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('account_type', models.CharField(choices=[('normal', 'Normal User'), ('technician', 'Technician')], default='normal', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(migrate_legacy_technician_accounts, reverse_migrate_legacy_technician_accounts),
    ]
