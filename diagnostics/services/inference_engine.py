"""
Expert System Inference Engine with Hybrid Reasoning + Enterprise Search.

Two entry points, ONE source of truth (DiagnosticRule nodes):
  1. Decision Tree:  question -> options -> next_node -> ... -> solution
  2. Direct Search: symptom query -> ranked matching nodes -> jump to any node

Both paths resolve to the same DiagnosticRule objects. No data duplication.
"""

import json
import logging
import re
from difflib import get_close_matches, SequenceMatcher
from collections import Counter

from django.db.models import Q, Count
from diagnostics.models import DiagnosticRule, RuleOption, SearchIndex
from .scanner import HardwareScanner
from .validation import DatabaseKBValidator

logger = logging.getLogger(__name__)


class InferenceEngine:
    """
    Unified inference engine supporting both tree navigation and symptom search.
    """

    FUZZY_CUTOFF = 0.55
    MAX_SEARCH_RESULTS = 10

    def __init__(self):
        self.scanner = HardwareScanner()
        self._check_database_integrity()

    def _check_database_integrity(self):
        """Runs background validation without breaking runtime loops."""
        validator = DatabaseKBValidator()
        is_valid, errors = validator.validate()
        if not is_valid:
            logger.critical(
                f"Inference Engine Warning: Live DB contains {len(errors)} validation conflicts."
            )

    def get_fallback_node(self, node_id, contextual_error):
        """High-availability fallback node to prevent UI/template crashes."""
        return {
            "node_id": node_id if node_id else "error_node",
            "type": "solution",
            "text": "System Routing Interface Warning",
            "diagnosis": "System Routing Interface Warning",
            "reasoning": (
                f"The core inference framework encountered a record recovery "
                f"or integrity mapping exception: {contextual_error}."
            ),
            "recommendation": (
                "Please ensure your migrations are completely updated and "
                "database seeds match standard specifications. Return to the "
                "dashboard and re-verify your path selection."
            ),
            "confidence": 100,
            "options": [],
            "search_match_score": 0,
            "match_reason": "fallback",
        }

    def _is_evidence_gate_node(self, node_id):
        return bool(node_id and re.fullmatch(r"[A-Z0-9]+-Q2", str(node_id)))

    def _generate_evidence_question(self, category, selected_option=None, solution_target=None):
        category_name = (category or "System").replace("-", " ").title()
        selected_text = selected_option or "this issue"
        solution_id = solution_target or "solution"
        evidence_node_id = f"{category}-Q2" if category else "VERIFY-Q2"
        if solution_target:
            evidence_node_id = f"{evidence_node_id}::{solution_target}"
        return {
            "node_id": evidence_node_id,
            "type": "question",
            "title": f"{category_name} Evidence Check",
            "category": category or "General",
            "severity": "MEDIUM",
            "text": (
                f"Before confirming the diagnosis for '{selected_text}', do you have a second symptom or measurement that matches this {category_name.lower()} issue?"
            ),
            "diagnosis": "",
            "reasoning": "The rule engine requires a second piece of evidence before final diagnosis to avoid false positives from a single symptom.",
            "recommendation": "Confirm the matching symptom and continue to the recommended fix.",
            "confidence": 75,
            "options": [
                {"text": "Yes, I have matching evidence and want the diagnosis", "next": solution_id},
                {"text": "No, I want to choose a different issue", "next": f"{category}-Q1" if category else ""},
            ],
            "related_rules": [],
        }

    def _parse_evidence_gate(self, node_id):
        if "::" not in str(node_id):
            return None, None
        base, solution_id = str(node_id).split("::", 1)
        category = base.split("-Q2", 1)[0] if "-Q2" in base else None
        return category, solution_id

    def get_node(self, node_id):
        """
        Retrieve a node from the database and build the JSON shape the UI expects.
        """
        evidence_category, evidence_solution = self._parse_evidence_gate(node_id)
        if self._is_evidence_gate_node(node_id) or evidence_solution:
            category = evidence_category or (node_id.split("-Q2", 1)[0] if "-Q2" in str(node_id) else "General")
            return self._generate_evidence_question(category, "the selected symptom", evidence_solution)

        try:
            rule = DiagnosticRule.objects.get(node_id=node_id)

            options = []
            if rule.node_type == "question":
                for opt in rule.options.all().select_related("next_node"):
                    target_id = ""
                    if opt.next_node:
                        target_id = opt.next_node.node_id
                        if opt.next_node.node_type == "solution":
                            target_id = f"{rule.category}-Q2::{opt.next_node.node_id}"
                    options.append({
                        "text": opt.option_text,
                        "next": target_id,
                    })

            return {
                "node_id": rule.node_id,
                "type": rule.node_type,
                "title": rule.title,
                "category": rule.category,
                "severity": rule.severity,
                "text": rule.content,
                "diagnosis": rule.content if rule.node_type == "solution" else "",
                "reasoning": rule.reasoning or "",
                "recommendation": rule.recommendation or "",
                "user_explanation": rule.user_explanation or "",
                "technician_explanation": rule.technician_explanation or "",
                "user_recommendation": rule.user_recommendation or "",
                "technician_recommendation": rule.technician_recommendation or "",
                "safety_warning": rule.safety_warning or "",
                "confidence": 80,
                "options": options,
                "related_rules": [
                    r.strip()
                    for r in rule.related_rules.split(",")
                    if r.strip()
                ] if rule.related_rules else [],
            }
        except DiagnosticRule.DoesNotExist:
            logger.error(f"Node '{node_id}' does not exist in active DB tables.")
            return self.get_fallback_node(node_id, "Node not found in storage.")
        except Exception as e:
            logger.critical(f"Critical exception parsing node '{node_id}': {str(e)}")
            return self.get_fallback_node(node_id, str(e))

    def process_step(self, current_node_id, selected_index=None):
        """
        Navigate the decision tree based on user selection.
        Returns: (next_node_dict, next_node_id)
        """
        current_node = self.get_node(current_node_id)

        if not current_node or current_node.get("diagnosis") == "System Routing Interface Warning":
            return self.get_fallback_node(current_node_id, "Navigation trace broken."), "error"

        if current_node["type"] == "question" and selected_index is not None:
            try:
                next_node_id = current_node["options"][selected_index]["next"]
                if not next_node_id:
                    return current_node, current_node_id

                if str(next_node_id).startswith("") and "::" in str(next_node_id):
                    pass

                if "::" in str(next_node_id):
                    next_node = self.get_node(next_node_id)
                    return next_node, next_node_id

                next_node = self.get_node(next_node_id)

                if next_node and next_node.get("type") == "solution":
                    next_node = self._apply_hybrid_logic(next_node)

                return next_node, next_node_id
            except (IndexError, KeyError, TypeError) as err:
                logger.warning(
                    f"Branch traversal failed at '{current_node_id}', "
                    f"option index '{selected_index}': {err}"
                )
                return current_node, current_node_id

        if current_node.get("type") == "question" and "::" in str(current_node_id):
            try:
                category, solution_id = self._parse_evidence_gate(current_node_id)
                if not solution_id:
                    return current_node, current_node_id
                if selected_index in (0, None):
                    next_node = self.get_node(solution_id)
                    if next_node and next_node.get("type") == "solution":
                        next_node = self._apply_hybrid_logic(next_node)
                    return next_node, solution_id
                if selected_index == 1:
                    root_id = f"{category}-Q1" if category else "CPU-Q1"
                    return self.get_node(root_id), root_id
            except (IndexError, KeyError, TypeError) as err:
                logger.warning(
                    f"Evidence check failed at '{current_node_id}', "
                    f"option index '{selected_index}': {err}"
                )
                return current_node, current_node_id

        return current_node, current_node_id

    def _apply_hybrid_logic(self, solution_node):
        """Adjust confidence and add evidence based on live hardware metrics."""
        try:
            stats = self.scanner.get_system_stats()
            cpu = stats.get("cpu_usage", 0)
            ram = stats.get("ram_usage", 0)
        except Exception as e:
            logger.error(f"Hardware scanner unavailable: {e}")
            return solution_node

        enhanced = solution_node.copy()
        evidence = []
        diagnosis = enhanced.get("diagnosis", "")

        if any(k in diagnosis for k in ["CPU", "Overheating", "Thermal", "Heat"]):
            if cpu > 70:
                enhanced["confidence"] = min(99, enhanced["confidence"] + 10)
                evidence.append(f"Live telemetry: high CPU load ({cpu}%).")
            elif cpu < 20:
                enhanced["confidence"] = max(50, enhanced["confidence"] - 15)
                evidence.append(f"CPU load low ({cpu}%) -- unlikely thermal issue.")

        if any(k in diagnosis for k in ["Memory", "RAM", "Memory Management"]):
            if ram > 80:
                enhanced["confidence"] = min(99, enhanced["confidence"] + 5)
                evidence.append(f"RAM at {ram}% -- supports memory bottleneck theory.")
            elif ram < 40:
                enhanced["confidence"] = max(40, enhanced["confidence"] - 20)
                evidence.append(f"RAM only {ram}% -- contradicts hardware failure.")

        if evidence:
            enhanced["reasoning"] += " | Evidence: " + " ".join(evidence)

        return enhanced

    def search_symptoms(self, query):
        """
        Enterprise-grade symptom search. Returns ranked list of matching nodes.
        4-Tier Search Strategy: Exact -> Index -> Category -> Fuzzy
        """
        if not query or len(query.strip()) < 2:
            return []

        clean_query = query.strip().lower()
        query_tokens = self._tokenize(clean_query)
        results = {}

        # Tier 1: Exact / icontains matching
        tier1_qs = DiagnosticRule.objects.filter(
            Q(node_id__icontains=clean_query) |
            Q(title__icontains=clean_query) |
            Q(content__icontains=clean_query) |
            Q(search_keywords__icontains=clean_query) |
            Q(category__icontains=clean_query)
        ).filter(is_active=True).distinct()

        for rule in tier1_qs[:self.MAX_SEARCH_RESULTS * 2]:
            score = self._calculate_exact_score(rule, clean_query)
            results[rule.node_id] = {
                "score": score,
                "match_reason": "exact_match",
                "rule": rule,
            }

        # Tier 2: SearchIndex token matching
        if len(results) < self.MAX_SEARCH_RESULTS:
            indexed_rules = (
                DiagnosticRule.objects
                .filter(search_terms__term__in=query_tokens, is_active=True)
                .annotate(match_count=Count("search_terms"))
                .filter(match_count__gte=1)
                .order_by("-match_count")
            )

            for rule in indexed_rules[:self.MAX_SEARCH_RESULTS * 2]:
                if rule.node_id in results:
                    results[rule.node_id]["score"] += rule.match_count * 5
                    results[rule.node_id]["match_reason"] = "exact+index"
                else:
                    results[rule.node_id] = {
                        "score": rule.match_count * 5,
                        "match_reason": "index_match",
                        "rule": rule,
                    }

        # Tier 3: Category inference
        if len(results) < self.MAX_SEARCH_RESULTS // 2:
            category_map = {
                "cpu": "CPU", "processor": "CPU", "overheat": "CPU",
                "ram": "RAM", "memory": "RAM", "memtest": "RAM",
                "disk": "Storage", "hdd": "Storage", "ssd": "Storage",
                "drive": "Storage", "storage": "Storage",
                "gpu": "GPU", "graphics": "GPU", "video": "GPU",
                "display": "Display", "screen": "Display", "monitor": "Display",
                "psu": "PSU", "power": "PSU", "supply": "PSU",
                "motherboard": "Motherboard", "mainboard": "Motherboard",
                "boot": "Boot", "startup": "Boot", "won't start": "Boot",
                "bios": "BIOS", "uefi": "BIOS",
                "network": "Network", "wifi": "Network", "ethernet": "Network",
                "internet": "Network", "bluetooth": "Network",
                "keyboard": "Peripherals", "mouse": "Peripherals",
                "usb": "Peripherals", "printer": "Peripherals",
                "audio": "Audio", "sound": "Audio", "speaker": "Audio",
                "microphone": "Audio", "headphone": "Audio",
                "laptop": "Laptop", "battery": "Laptop", "hinge": "Laptop",
                "fan": "Laptop", "touchpad": "Laptop",
                "windows": "General", "update": "General", "bsod": "General",
                "slow": "General", "crash": "General",
            }
            inferred_categories = set()
            for token in query_tokens:
                if token in category_map:
                    inferred_categories.add(category_map[token])

            if inferred_categories:
                cat_qs = DiagnosticRule.objects.filter(
                    category__in=inferred_categories,
                    is_active=True
                ).exclude(node_id__in=results.keys())

                for rule in cat_qs[:self.MAX_SEARCH_RESULTS]:
                    results[rule.node_id] = {
                        "score": 15,
                        "match_reason": "category_inference",
                        "rule": rule,
                    }

        # Tier 4: Fuzzy spelling correction
        if len(results) < 3:
            all_terms = list(
                SearchIndex.objects
                .values_list("term", flat=True)
                .distinct()
            )
            fuzzy_matches = []
            for token in query_tokens:
                if len(token) >= 3:
                    close = get_close_matches(
                        token, all_terms, n=3, cutoff=self.FUZZY_CUTOFF
                    )
                    fuzzy_matches.extend(close)

            if fuzzy_matches:
                fuzzy_rules = (
                    DiagnosticRule.objects
                    .filter(search_terms__term__in=fuzzy_matches, is_active=True)
                    .annotate(match_count=Count("search_terms"))
                    .exclude(node_id__in=results.keys())
                    .order_by("-match_count")
                )
                for rule in fuzzy_rules[:5]:
                    results[rule.node_id] = {
                        "score": 10,
                        "match_reason": "fuzzy_match",
                        "rule": rule,
                    }

        # Rank and format results
        ranked = sorted(results.values(), key=lambda x: x["score"], reverse=True)

        output = []
        for item in ranked[:self.MAX_SEARCH_RESULTS]:
            rule = item["rule"]
            node_dict = self.get_node(rule.node_id)
            node_dict["search_match_score"] = item["score"]
            node_dict["match_reason"] = item["match_reason"]
            output.append(node_dict)

        return output

    def _tokenize(self, text):
        """Split query into searchable tokens."""
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = re.sub(r"[^a-zA-Z0-9 ]", " ", clean)
        tokens = [t.lower() for t in clean.split() if len(t) >= 2]
        bigrams = []
        for i in range(len(tokens) - 1):
            bigrams.append(f"{tokens[i]} {tokens[i+1]}")
        return tokens + bigrams

    def _calculate_exact_score(self, rule, query):
        """Score a rule based on how strongly it matches the exact query."""
        score = 0
        q = query.lower()

        if q == rule.node_id.lower():
            score += 100
        elif q in rule.node_id.lower():
            score += 50

        if q in rule.title.lower():
            score += 40

        if q in rule.content.lower():
            score += 30

        if rule.search_keywords and q in rule.search_keywords.lower():
            score += 35

        if q in rule.category.lower():
            score += 20

        return score

    def get_tree_root(self):
        """
        Return the root node of the decision tree.
        """
        roots = DiagnosticRule.objects.filter(
            node_type="question", is_active=True
        ).order_by("node_id")

        if not roots.exists():
            roots = DiagnosticRule.objects.filter(is_active=True).order_by("node_id")

        if roots.exists():
            return self.get_node(roots.first().node_id)
        return self.get_fallback_node(None, "No root node found in database.")
    
    def get_all_roots(self):
        """Return ALL root nodes across all categories for browse UI."""
        roots = DiagnosticRule.objects.filter(
            node_type="question", is_active=True
        ).order_by("category", "node_id")
        return [self.get_node(r.node_id) for r in roots]
    
    def get_all_nodes(self):
        """Return ALL active nodes for full tree verification."""
        nodes = DiagnosticRule.objects.filter(is_active=True).order_by("node_id")
        return [self.get_node(n.node_id) for n in nodes]
    
    def get_all_categories(self):
        """Return list of all active categories for browse/filter UI."""
        return (
            DiagnosticRule.objects
            .filter(is_active=True)
            .values_list("category", flat=True)
            .distinct()
            .order_by("category")
        )