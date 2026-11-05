"""
Django signals for maintaining the SearchIndex automatically.
Auto-rebuilds when DiagnosticRule or RuleOption changes.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import DiagnosticRule, RuleOption, SearchIndex


@receiver(post_save, sender=DiagnosticRule)
def rebuild_index_on_rule_save(sender, instance, created, **kwargs):
    """Rebuild search index when a rule is created or updated."""
    instance.rebuild_search_index()


@receiver(post_delete, sender=DiagnosticRule)
def cleanup_index_on_rule_delete(sender, instance, **kwargs):
    """Remove search index entries when a rule is deleted."""
    SearchIndex.objects.filter(rule=instance).delete()


@receiver(post_save, sender=RuleOption)
def rebuild_index_on_option_save(sender, instance, created, **kwargs):
    """Rebuild parent rule's index when an option is added/changed."""
    if instance.rule:
        instance.rule.rebuild_search_index()


@receiver(post_delete, sender=RuleOption)
def rebuild_index_on_option_delete(sender, instance, **kwargs):
    """Rebuild parent rule's index when an option is removed."""
    if instance.rule:
        instance.rule.rebuild_search_index()