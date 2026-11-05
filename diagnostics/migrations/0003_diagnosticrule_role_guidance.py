from django.db import migrations, models


def create_technician_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Technician")


def remove_technician_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Technician").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("diagnostics", "0002_hardwarehealthlog_battery_percent_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="diagnosticrule",
            name="user_explanation",
            field=models.TextField(blank=True, help_text="Optional plain-language explanation for normal users"),
        ),
        migrations.AddField(
            model_name="diagnosticrule",
            name="technician_explanation",
            field=models.TextField(blank=True, help_text="Optional technical explanation for technicians"),
        ),
        migrations.AddField(
            model_name="diagnosticrule",
            name="user_recommendation",
            field=models.TextField(blank=True, help_text="Optional safe procedure for normal users"),
        ),
        migrations.AddField(
            model_name="diagnosticrule",
            name="technician_recommendation",
            field=models.TextField(blank=True, help_text="Optional advanced procedure for technicians"),
        ),
        migrations.AddField(
            model_name="diagnosticrule",
            name="safety_warning",
            field=models.TextField(blank=True, help_text="Safety warning shown with diagnostic guidance"),
        ),
        migrations.RunPython(create_technician_group, remove_technician_group),
    ]