from django.core.management.base import BaseCommand

from diagnostics.services.user_inference_engine import seed_user_diagnostic_cases


class Command(BaseCommand):
    help = "Seed the Normal User diagnostic knowledge base without altering the Technician knowledge base."

    def handle(self, *args, **options):
        count = seed_user_diagnostic_cases()
        self.stdout.write(self.style.SUCCESS(f"Normal User KB seeded: {count} cases"))
