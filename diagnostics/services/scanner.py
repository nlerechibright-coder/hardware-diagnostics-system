import psutil
import platform
import json
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


THRESHOLD_COLORS = {
    'cpu': [
        (0, 50, 'success', 'Healthy', '#28a745'),
        (50, 70, 'warning', 'Warning', '#ffc107'),
        (70, 85, 'orange', 'Critical Warning', '#fd7e14'),
        (85, 100, 'danger', 'Critical', '#dc3545'),
    ],
    'ram': [
        (0, 50, 'success', 'Healthy', '#28a745'),
        (50, 70, 'warning', 'Warning', '#ffc107'),
        (70, 85, 'orange', 'Critical Warning', '#fd7e14'),
        (85, 100, 'danger', 'Critical', '#dc3545'),
    ],
    'disk': [
        (0, 60, 'success', 'Healthy', '#28a745'),
        (60, 75, 'warning', 'Warning', '#ffc107'),
        (75, 90, 'orange', 'Critical Warning', '#fd7e14'),
        (90, 100, 'danger', 'Critical', '#dc3545'),
    ],
    'battery': [
        (50, 100, 'success', 'Healthy', '#28a745'),
        (30, 50, 'warning', 'Warning', '#ffc107'),
        (15, 30, 'orange', 'Critical Warning', '#fd7e14'),
        (0, 15, 'danger', 'Critical', '#dc3545'),
    ],
}


def get_status_color(metric_type, percent):
    """
    Determine color status for a metric based on percentage.
    Returns dict with: css_class, label, hex, level
    """
    if metric_type not in THRESHOLD_COLORS:
        return {'css_class': 'secondary', 'label': 'Unknown', 'hex': '#6c757d', 'level': -1}
    
    for level, (low, high, css_class, label, hex_color) in enumerate(THRESHOLD_COLORS[metric_type]):
        if low <= percent <= high:
            return {
                'css_class': css_class,
                'label': label,
                'hex': hex_color,
                'level': level,
            }
    
    bands = THRESHOLD_COLORS[metric_type]
    if percent < bands[0][0]:
        return {'css_class': bands[0][2], 'label': bands[0][3], 'hex': bands[0][4], 'level': 0}
    else:
        last = bands[-1]
        return {'css_class': last[2], 'label': last[3], 'hex': last[4], 'level': len(bands) - 1}


class HardwareScanner:
    """
    Utility service to capture real-time system metrics.
    Optimized for integration with the Diagnostic Inference Engine.
    """

    @staticmethod
    def get_system_stats():
        """Captures raw hardware utilization data from the operating system."""
        try:
            battery = psutil.sensors_battery()
            return {
                "os": platform.system(),
                "cpu_usage": psutil.cpu_percent(interval=0.5),
                "ram_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "cpu_count": psutil.cpu_count(logical=True),
                "battery": battery.percent if battery else 100,
            }
        except Exception as e:
            logger.error(f"HardwareScanner.get_system_stats() failed: {e}")
            return {"error": f"Scanner Failure: {str(e)}"}

    def get_diagnosis(self):
        """
        Threshold-based diagnostic logic for real-time dashboard alerts.
        Cross-references live OS stats against the Knowledge Base JSON file.
        Returns current hardware metrics plus any threshold violations.
        """
        stats = self.get_system_stats()
        if "error" in stats:
            return {
                "current_stats": {
                    "cpu_usage": None,
                    "ram_usage": None,
                    "disk_usage": None,
                    "battery": None
                },
                "diagnostics": [],
                "overall_status": "UNKNOWN",
                "scanner_error": stats["error"]
            }

        kb_path = getattr(
            settings, 'KB_FILE_PATH',
            os.path.join(settings.BASE_DIR, 'diagnostics', 'data', 'hardware_kb.json')
        )
        results = []

        if os.path.exists(kb_path):
            try:
                with open(kb_path, 'r', encoding='utf-8') as f:
                    kb_data = json.load(f)

                for rule in kb_data.get('diagnostics', []):
                    component = rule['component']
                    threshold = rule['threshold']
                    val = None

                    component_lower = component.lower()
                    if 'cpu' in component_lower or 'processor' in component_lower:
                        val = stats.get('cpu_usage')
                    elif 'ram' in component_lower or 'memory' in component_lower:
                        val = stats.get('ram_usage')
                    elif 'disk' in component_lower or 'storage' in component_lower or 'hdd' in component_lower or 'ssd' in component_lower:
                        val = stats.get('disk_usage')
                    elif 'power' in component_lower or 'psu' in component_lower or 'voltage' in component_lower:
                        val = stats.get('cpu_usage')
                    elif 'cooling' in component_lower or 'fan' in component_lower or 'thermal' in component_lower:
                        val = stats.get('cpu_usage')
                    elif 'battery' in component_lower:
                        val = stats.get('battery')

                    if val is not None:
                        is_critical = False
                        is_warning = False

                        if 'battery' in component_lower:
                            if val <= threshold:
                                is_critical = True
                            elif val <= (threshold + 10):
                                is_warning = True
                        elif 'power' in component_lower or 'voltage' in component_lower or 'psu' in component_lower:
                            if val >= 90:
                                is_critical = True
                            elif val >= 75:
                                is_warning = True
                        else:
                            if val >= threshold:
                                is_critical = True
                            elif val >= (threshold - 15):
                                is_warning = True

                        if is_critical:
                            results.append({
                                "id": rule.get('id', 'UNKNOWN'),
                                "component": rule['component'],
                                "issue": rule['issue'],
                                "recommendation": rule['recommendation'],
                                "status": "CRITICAL",
                                "value": val,
                                "threshold": threshold
                            })
                        elif is_warning:
                            results.append({
                                "id": rule.get('id', 'WARN'),
                                "component": rule['component'],
                                "issue": f"Elevated {rule['component']} Activity",
                                "recommendation": "Performance may degrade. Review active processes and system load.",
                                "status": "WARNING",
                                "value": val,
                                "threshold": threshold
                            })

            except (json.JSONDecodeError, KeyError, IOError) as e:
                logger.warning(f"Failed to parse KB file at {kb_path}: {e}")
        else:
            logger.warning(f"KB file not found at {kb_path}. Running without threshold diagnostics.")

        color_status = {}
        for metric in ['cpu_usage', 'ram_usage', 'disk_usage', 'battery']:
            val = stats.get(metric)
            if val is not None:
                threshold_key = metric.replace('_usage', '')
                if threshold_key == 'battery':
                    threshold_key = 'battery'
                color_status[metric] = get_status_color(threshold_key, val)
            else:
                color_status[metric] = get_status_color('cpu', 0)

        return {
            "current_stats": {
                "cpu_usage": stats.get('cpu_usage'),
                "ram_usage": stats.get('ram_usage'),
                "disk_usage": stats.get('disk_usage'),
                "battery": stats.get('battery')
            },
            "color_status": color_status,
            "diagnostics": results,
            "overall_status": "UNHEALTHY" if any(r['status'] == "CRITICAL" for r in results) else "HEALTHY"
        }

    def save_snapshot(self, user=None, session=None):
        """
        Saves a hardware health snapshot to the database for historical analysis.
        """
        try:
            from diagnostics.models import HardwareHealthLog

            stats = self.get_system_stats()
            if "error" in stats:
                logger.warning("Cannot save snapshot: scanner returned error.")
                return None

            status_label = "HEALTHY"
            if stats.get('cpu_usage', 0) > 85 or stats.get('ram_usage', 0) > 85:
                status_label = "UNHEALTHY"

            snapshot = HardwareHealthLog.objects.create(
                cpu_usage=stats.get('cpu_usage', 0.0),
                ram_usage=stats.get('ram_usage', 0.0),
                disk_usage=stats.get('disk_usage', 0.0),
                battery_percent=stats.get('battery'),
                status_label=status_label,
                session=session
            )
            logger.info(f"Hardware snapshot saved: ID={snapshot.id}, CPU={snapshot.cpu_usage}%")
            return snapshot
        except Exception as e:
            logger.error(f"Failed to save hardware snapshot: {e}")
            return None