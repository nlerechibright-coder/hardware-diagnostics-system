import logging
from diagnostics.models import DiagnosticRule, RuleOption

logger = logging.getLogger(__name__)


class KBValidationError(Exception):
    """Base exception for all Knowledge Base schema or validation errors."""
    pass


class DatabaseKBValidator:
    def __init__(self):
        self.errors = []

    def validate(self):
        """Executes a full validation suite on the live database records."""
        try:
            rules = DiagnosticRule.objects.all()
            if not rules.exists():
                self.errors.append("The DiagnosticRule database table is completely empty.")
                return False, self.errors

            self._validate_node_structures(rules)

            if not self.errors:
                self._validate_graph_logic(rules)

        except Exception as e:
            self.errors.append(f"Database access exception during validation execution: {str(e)}")

        is_valid = len(self.errors) == 0
        if not is_valid:
            for error in self.errors:
                logger.error(f"[KB VALIDATION FAILURE] {error}")
        
        return is_valid, self.errors

    def _validate_node_structures(self, rules):
        for rule in rules:
            if rule.node_type not in ['question', 'solution']:
                self.errors.append(f"Node ID '{rule.node_id}' has an invalid type: '{rule.node_type}'. Expected 'question' or 'solution'.")
                continue

            if not rule.content or not rule.content.strip():
                self.errors.append(f"Node ID '{rule.node_id}' has missing or empty content.")

            if rule.node_type == 'question':
                options = RuleOption.objects.filter(rule=rule)
                if not options.exists():
                    self.errors.append(f"Question node ID '{rule.node_id}' provides no attached choice options.")
                else:
                    for idx, opt in enumerate(options):
                        opt_text = getattr(opt, 'text', '') or getattr(opt, 'option_text', '')
                        if not opt_text or not opt_text.strip():
                            self.errors.append(f"Question node ID '{rule.node_id}' option index {idx} has missing choice text.")
                        if not opt.next_node:
                            self.errors.append(f"Question node ID '{rule.node_id}' option index {idx} has a null next_node link.")

            elif rule.node_type == 'solution':
                if not getattr(rule, 'reasoning', '').strip():
                    self.errors.append(f"Solution node ID '{rule.node_id}' requires a populated reasoning field.")
                if not getattr(rule, 'recommendation', '').strip():
                    self.errors.append(f"Solution node ID '{rule.node_id}' requires a populated recommendation field.")

    def _validate_graph_logic(self, rules):
        rule_map = {r.node_id: r for r in rules}

        for rule in rules:
            if rule.node_type == 'question':
                options = RuleOption.objects.filter(rule=rule)
                for opt in options:
                    if opt.next_node:
                        target_id = getattr(opt.next_node, 'node_id', str(opt.next_node))
                        if target_id not in rule_map:
                            self.errors.append(f"Broken Route Link: Question node ID '{rule.node_id}' references a non-existent next target ID: '{target_id}'.")

        visited = set()
        rec_stack = set()

        def has_cycle(curr_id):
            visited.add(curr_id)
            rec_stack.add(curr_id)

            rule = rule_map.get(curr_id)
            if rule and rule.node_type == 'question':
                options = RuleOption.objects.filter(rule=rule)
                for opt in options:
                    if opt.next_node:
                        nxt_id = getattr(opt.next_node, 'node_id', str(opt.next_node))
                        if nxt_id in rec_stack:
                            return True, [nxt_id, curr_id]
                        if nxt_id not in visited and nxt_id in rule_map:
                            cycle_found, path = has_cycle(nxt_id)
                            if cycle_found:
                                return True, path + [curr_id]

            rec_stack.remove(curr_id)
            return False, []

        for node_id in rule_map.keys():
            if node_id not in visited:
                contains_loop, loop_path = has_cycle(node_id)
                if contains_loop:
                    path_str = " -> ".join(reversed(loop_path))
                    self.errors.append(f"Infinite Execution Loop Detected: Circuit pathway triggers a cycle: ({path_str}).")
                    break