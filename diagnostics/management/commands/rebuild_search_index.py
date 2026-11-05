"""
Management command to rebuild the SearchIndex from all active DiagnosticRules.

Usage:
    python manage.py rebuild_search_index
"""

from django.core.management.base import BaseCommand
from diagnostics.models import DiagnosticRule, SearchIndex


class Command(BaseCommand):
    help = "Rebuilds the SearchIndex for all active DiagnosticRules."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be indexed without writing to DB.",
        )

    def handle(self, *args, **options):
        self.stdout.write("Rebuilding search index...")

        rules = DiagnosticRule.objects.filter(is_active=True)
        total_rules = rules.count()

        if not total_rules:
            self.stdout.write(self.style.WARNING("  No active rules found."))
            return

        if options["dry_run"]:
            self.stdout.write(f"  Would index {total_rules} rules (dry run).")
            for rule in rules:
                terms = rule.get_search_terms()
                self.stdout.write(f"    {rule.node_id}: {len(terms)} terms")
            return

        SearchIndex.objects.all().delete()
        total_terms = 0

        for rule in rules:
            rule.rebuild_search_index()
            count = SearchIndex.objects.filter(rule=rule).count()
            total_terms += count

        self.stdout.write(self.style.SUCCESS(
            f"Search index rebuilt successfully!"
            f"   Rules indexed: {total_rules}"
            f"   Total search terms: {total_terms}"
        ))