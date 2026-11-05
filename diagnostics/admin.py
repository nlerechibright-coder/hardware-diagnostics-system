from django.contrib import admin
from .models import DiagnosticRule, RuleOption, DiagnosticSession, HardwareHealthLog, SearchIndex


class RuleOptionInline(admin.TabularInline):
    model = RuleOption
    fk_name = "rule"
    extra = 2


@admin.register(DiagnosticRule)
class DiagnosticRuleAdmin(admin.ModelAdmin):
    list_display = ('node_id', 'node_type', 'title', 'category', 'severity', 'is_active')
    list_filter = ('node_type', 'category', 'severity', 'is_active')
    search_fields = ('node_id', 'title', 'content', 'search_keywords')
    inlines = [RuleOptionInline]


@admin.register(DiagnosticSession)
class DiagnosticSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'status', 'started_at', 'completed_at')
    list_filter = ('status',)
    search_fields = ('session_id',)
    readonly_fields = ('started_at', 'updated_at')


@admin.register(HardwareHealthLog)
class HardwareHealthLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'cpu_usage', 'ram_usage', 'battery_percent', 'status_label', 'recorded_at')
    list_filter = ('status_label', 'recorded_at')
    readonly_fields = ('recorded_at',)


@admin.register(SearchIndex)
class SearchIndexAdmin(admin.ModelAdmin):
    list_display = ('term', 'rule')
    list_filter = ('rule__category',)
    search_fields = ('term', 'rule__node_id')