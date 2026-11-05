from .roles import get_role_name, is_technician


def _safe_normal_user_explanation(node):
    diagnosis = (node.get("diagnosis") or node.get("title") or "this issue").strip()
    safety = (node.get("safety_warning") or "").strip()
    if safety:
        return (
            f"This issue may need attention: {diagnosis}. Follow the safety guidance and "
            "power the device down before checking anything, and work safely. If you are not "
            "comfortable with the steps, contact a qualified technician for help."
        )
    return (
        f"This issue may need attention: {diagnosis}. Follow safe basic steps, power the device "
        "down before checking anything, work safely, and contact a qualified technician if you are unsure."
    )


def _safe_normal_user_procedure(node):
    user_recommendation = (node.get("user_recommendation") or "").strip()
    if user_recommendation:
        return user_recommendation

    safety = (node.get("safety_warning") or "").strip()
    if safety:
        return (
            "Power the device off and disconnect it from power before checking anything. "
            "Follow the safety guidance and contact a qualified technician if you are not comfortable "
            "performing the steps."
        )
    return (
        "Power the device off and disconnect it from power before checking any components. "
        "If the issue is unclear or you are unsure, contact a qualified technician."
    )


def present_node(node, user):
    """Present one shared inference node at the appropriate technical depth."""
    if not node:
        return node

    if node.get("audience") == "user" and ("explanation" in node or "procedure" in node):
        presented = dict(node)
        presented["role_label"] = get_role_name(user)
        return presented

    if node.get("audience") == "technician" and ("technical_reasoning" in node or "advanced_procedure" in node):
        presented = dict(node)
        presented["role_label"] = get_role_name(user)
        return presented

    presented = dict(node)
    presented["audience"] = "technician" if is_technician(user) else "user"
    presented["role_label"] = get_role_name(user)

    if node.get("type") != "solution":
        return presented

    if is_technician(user):
        presented["explanation"] = node.get("technician_explanation") or node.get("reasoning", "")
        presented["procedure"] = node.get("technician_recommendation") or node.get("recommendation", "")
        presented["technical_reasoning"] = node.get("reasoning", "")
        presented["advanced_procedure"] = node.get("technician_recommendation") or node.get("recommendation", "")
        presented["safety_warning"] = node.get("safety_warning", "")
        return presented

    presented["explanation"] = node.get("user_explanation") or _safe_normal_user_explanation(node)
    presented["procedure"] = _safe_normal_user_procedure(node)
    presented.pop("technical_reasoning", None)
    presented.pop("advanced_procedure", None)
    presented.pop("technician_explanation", None)
    presented.pop("technician_recommendation", None)
    presented["safety_warning"] = node.get("safety_warning", "")
    return presented