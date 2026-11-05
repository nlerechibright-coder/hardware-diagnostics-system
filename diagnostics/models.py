"""
Diagnostics models — Decision Tree + SearchIndex (single source of truth).
Includes legacy DiagnosticSession and HardwareHealthLog for backward compatibility.
"""

from django.conf import settings
from django.db import models
import re


class DiagnosticRule(models.Model):
    """
    A node in the decision tree. Can be a question (with options) or a solution.
    Also serves as the target for direct symptom search.
    """
    NODE_TYPES = [
        ("question", "Question"),
        ("solution", "Solution"),
    ]
    SEVERITY_LEVELS = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical"),
    ]

    node_id = models.CharField(max_length=50, unique=True, db_index=True)
    category = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=200)
    node_type = models.CharField(max_length=20, choices=NODE_TYPES, default="solution")
    content = models.TextField(help_text="Question text or full diagnostic article")
    reasoning = models.TextField(blank=True, help_text="Why this diagnosis applies")
    recommendation = models.TextField(blank=True, help_text="Recommended next steps")
    user_explanation = models.TextField(blank=True, help_text="Optional plain-language explanation for normal users")
    technician_explanation = models.TextField(blank=True, help_text="Optional technical explanation for technicians")
    user_recommendation = models.TextField(blank=True, help_text="Optional safe procedure for normal users")
    technician_recommendation = models.TextField(blank=True, help_text="Optional advanced procedure for technicians")
    safety_warning = models.TextField(blank=True, help_text="Safety warning shown with diagnostic guidance")
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS, default="MEDIUM")
    search_keywords = models.TextField(
        blank=True,
        help_text="Comma-separated keywords for search matching"
    )
    related_rules = models.CharField(
        max_length=500, blank=True,
        help_text="Comma-separated node_ids of related rules"
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "node_id"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["node_type", "is_active"]),
            models.Index(fields=["severity", "is_active"]),
        ]

    def __str__(self):
        return f"[{self.node_id}] {self.title}"

    def get_search_terms(self):
        """
        Extract all searchable terms from this rule for the SearchIndex.
        Includes: node_id, title, content words, search_keywords, category.
        """
        terms = set()

        # Node ID tokens
        terms.add(self.node_id.lower())
        terms.add(self.node_id.lower().replace("-", ""))
        if "-" in self.node_id:
            parts = self.node_id.lower().split("-")
            terms.update(parts)

        # Title words
        title_words = re.findall(r"[a-zA-Z0-9]+", self.title.lower())
        terms.update(title_words)

        # Content words (first 200 words)
        content_clean = re.sub(r"<[^>]+>", " ", self.content)
        content_words = re.findall(r"[a-zA-Z]{3,}", content_clean.lower())
        terms.update(content_words[:200])

        # Explicit keywords
        if self.search_keywords:
            kw_terms = [t.strip().lower() for t in self.search_keywords.split(",")]
            terms.update(kw_terms)

        # Category
        terms.add(self.category.lower())

        # Severity
        terms.add(self.severity.lower())

        # Bigrams from title
        title_clean = re.sub(r"[^a-zA-Z0-9 ]", " ", self.title.lower())
        title_tokens = [t for t in title_clean.split() if len(t) > 2]
        for i in range(len(title_tokens) - 1):
            terms.add(f"{title_tokens[i]} {title_tokens[i+1]}")

        # Filter: minimum 2 chars, no pure numbers under 3 digits
        filtered = set()
        for t in terms:
            t = t.strip()
            if len(t) >= 2:
                if t.isdigit() and len(t) < 3:
                    continue
                filtered.add(t)

        return filtered

    def rebuild_search_index(self):
        """Rebuild SearchIndex entries for this rule. Called by signals."""
        SearchIndex.objects.filter(rule=self).delete()
        terms = self.get_search_terms()
        SearchIndex.objects.bulk_create([
            SearchIndex(rule=self, term=term)
            for term in terms
        ])


class RuleOption(models.Model):
    """
    A branching option attached to a question-type DiagnosticRule.
    Defines the decision tree edges.
    """
    rule = models.ForeignKey(
        DiagnosticRule, on_delete=models.CASCADE,
        related_name="options"
    )
    option_text = models.CharField(max_length=300)
    next_node = models.ForeignKey(
        DiagnosticRule, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="incoming_edges"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.rule.node_id} -> {self.next_node.node_id if self.next_node else 'END'}: {self.option_text[:50]}"


class SearchIndex(models.Model):
    """
    Pre-computed search terms for fast symptom lookup.
    Auto-maintained via Django signals. One source of truth: DiagnosticRule.
    """
    rule = models.ForeignKey(
        DiagnosticRule, on_delete=models.CASCADE,
        related_name="search_terms"
    )
    term = models.CharField(max_length=100, db_index=True)

    class Meta:
        unique_together = ["rule", "term"]
        indexes = [
            models.Index(fields=["term"]),
            models.Index(fields=["term", "rule"]),
        ]

    def __str__(self):
        return f"{self.term} -> {self.rule.node_id}"


class DiagnosticSession(models.Model):
    """
    Tracks a user's diagnostic session through the decision tree.
    Preserved for backward compatibility with existing admin/views.
    """
    SESSION_STATUS = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("abandoned", "Abandoned"),
    ]
    DIAGNOSTIC_SUBSYSTEM = [
        ("technician", "Technician"),
        ("normal_user", "Normal User"),
    ]

    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    user = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE,
        null=True, blank=True, related_name="diagnostic_sessions"
    )
    current_node = models.ForeignKey(
        DiagnosticRule, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="active_sessions"
    )
    diagnostic_subsystem = models.CharField(
        max_length=20,
        choices=DIAGNOSTIC_SUBSYSTEM,
        default="technician",
        db_index=True,
    )
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default="active")
    path_taken = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Session {self.session_id} ({self.status})"


class HardwareHealthLog(models.Model):
    """
    Logs hardware telemetry snapshots during diagnostic sessions.
    Preserved for backward compatibility with existing admin/views.
    """
    session = models.ForeignKey(
        DiagnosticSession, on_delete=models.CASCADE,
        related_name="health_logs", null=True, blank=True
    )
    cpu_usage = models.FloatField(null=True, blank=True)
    ram_usage = models.FloatField(null=True, blank=True)
    disk_usage = models.FloatField(null=True, blank=True)
    gpu_usage = models.FloatField(null=True, blank=True)
    cpu_temp = models.FloatField(null=True, blank=True)
    gpu_temp = models.FloatField(null=True, blank=True)
    battery_percent = models.FloatField(null=True, blank=True)
    status_label = models.CharField(max_length=50, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"HealthLog {self.id} @ {self.recorded_at.strftime('%Y-%m-%d %H:%M')}"


class UserProfile(models.Model):
    """Persistent application role source of truth for each authenticated user."""
    ACCOUNT_TYPE_CHOICES = [
        ("normal", "Normal User"),
        ("technician", "Technician"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default="normal",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.username}: {self.get_account_type_display()}"


class NormalUserDiagnosticCase(models.Model):
    """Simple separate diagnostic flow for ordinary computer users."""
    case_id = models.CharField(max_length=50, unique=True, db_index=True)
    category = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=200)
    question = models.TextField(blank=True, default="")
    diagnosis = models.TextField(blank=True, default="")
    explanation = models.TextField(blank=True, default="")
    procedure = models.TextField(blank=True, default="")
    warning = models.TextField(blank=True, default="")
    option_yes_text = models.CharField(max_length=200, default="Yes")
    option_no_text = models.CharField(max_length=200, default="No")
    next_yes = models.CharField(max_length=50, blank=True, default="")
    next_no = models.CharField(max_length=50, blank=True, default="")
    is_root = models.BooleanField(default=False, db_index=True)
    is_solution = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "case_id"]

    def __str__(self):
        return f"[{self.case_id}] {self.title}"