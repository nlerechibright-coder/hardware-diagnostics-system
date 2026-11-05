from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from diagnostics.models import NormalUserDiagnosticCase


class UserInferenceEngine:
    """Simple Normal User diagnostic engine that is independent of the Technician engine."""

    CASES = {
        "user-root": {
            "case_id": "user-root",
            "category": "general",
            "title": "Computer problem check",
            "question": "What is the main problem you are seeing?",
            "options": [
                {"text": "The computer will not turn on", "next": "user-power"},
                {"text": "The computer turns on but shows no display", "next": "user-display"},
                {"text": "The computer is overheating or shutting down", "next": "user-overheat"},
                {"text": "The computer is running slowly or freezing", "next": "user-slow"},
                {"text": "The computer will not boot or starts but fails to load", "next": "user-boot"},
                {"text": "The battery or charging is not working", "next": "user-battery"},
                {"text": "The keyboard, mouse, or USB device is not working", "next": "user-peripheral"},
                {"text": "The Wi-Fi, Bluetooth, or sound is not working", "next": "user-connectivity"},
            ],
            "is_root": True,
            "is_solution": False,
        },
        "user-power": {
            "case_id": "user-power",
            "category": "power",
            "title": "Computer won't turn on",
            "question": "Does the power light or fan come on at all when you press the power button?",
            "options": [
                {"text": "No, nothing happens", "next": "user-power-no-light"},
                {"text": "The light or fan comes on briefly", "next": "user-power-flicker"},
                {"text": "The computer starts but shuts off quickly", "next": "user-power-shutdown"},
            ],
            "is_root": False,
            "is_solution": False,
        },
        "user-power-no-light": {
            "case_id": "user-power-no-light",
            "category": "power",
            "title": "No power signs",
            "diagnosis": "Power issue or connection problem",
            "explanation": "The system may not be receiving stable power. Check the wall outlet, charger, and power cable before opening the case.",
            "procedure": "Try a different wall outlet, check that the cable is fully seated, and verify the charger or power adapter is working. If you are unsure, contact a qualified technician.",
            "warning": "Do not open the power supply or work inside the device if you are not comfortable doing so.",
            "is_solution": True,
        },
        "user-power-flicker": {
            "case_id": "user-power-flicker",
            "category": "power",
            "title": "Power flicker",
            "diagnosis": "Unstable power or component connection",
            "explanation": "A brief power flicker can mean a loose connection or a failing power adapter or battery setup.",
            "procedure": "Disconnect and reconnect the power cable, remove and reconnect the battery if applicable, and try again. If the issue keeps happening, contact a technician.",
            "warning": "Do not keep forcing the power button repeatedly if the unit is flickering or unstable.",
            "is_solution": True,
        },
        "user-power-shutdown": {
            "case_id": "user-power-shutdown",
            "category": "power",
            "title": "Computer turns off quickly",
            "diagnosis": "Overheating or unstable power",
            "explanation": "If the computer starts and then powers off fast, overheating or power instability is a likely cause.",
            "procedure": "Power it off, unplug it, and make sure the vents are clear of dust. Let it cool down before testing again. If it continues to shut down, contact a technician.",
            "warning": "Do not block vent openings or keep the device running in a hot room.",
            "is_solution": True,
        },
        "user-display": {
            "case_id": "user-display",
            "category": "display",
            "title": "No display",
            "question": "Does the computer start, but the screen stays black or blank?",
            "options": [
                {"text": "The screen stays black and the computer seems on", "next": "user-display-black"},
                {"text": "The screen flickers or shows a flashing signal", "next": "user-display-flicker"},
                {"text": "The screen is dim or unreadable", "next": "user-display-brightness"},
            ],
            "is_solution": False,
        },
        "user-display-black": {
            "case_id": "user-display-black",
            "category": "display",
            "title": "Black screen",
            "diagnosis": "Display or connection problem",
            "explanation": "The system may be starting normally but the display connection or display hardware may not be working correctly.",
            "procedure": "Check that the monitor cable is firmly connected, try a different cable or port, and confirm the monitor is powered on. If you have a laptop, check the brightness keys. If the issue remains, contact a technician.",
            "warning": "Do not repeatedly unplug and replug display cables while the machine is still powered on.",
            "is_solution": True,
        },
        "user-display-flicker": {
            "case_id": "user-display-flicker",
            "category": "display",
            "title": "Screen flicker",
            "diagnosis": "Display instability",
            "explanation": "A flickering screen can be caused by a loose cable, driver issue, or failing display hardware.",
            "procedure": "Restart the computer, update the display driver, and reconnect the display cable. If the flicker continues on different screens, contact a technician.",
            "warning": "If the screen flickers and the machine starts to overheat, power it down and let it cool.",
            "is_solution": True,
        },
        "user-display-brightness": {
            "case_id": "user-display-brightness",
            "category": "display",
            "title": "Dim or unreadable screen",
            "diagnosis": "Brightness or display setting problem",
            "explanation": "The brightness may be set too low or the display may not be receiving a clean signal.",
            "procedure": "Use the brightness keys, check the display settings, and verify the monitor is not in a power-saving mode. If the problem persists, contact a technician.",
            "warning": "Do not use a damaged screen or exposed cable that feels hot to the touch.",
            "is_solution": True,
        },
        "user-overheat": {
            "case_id": "user-overheat",
            "category": "thermal",
            "title": "Overheating or shutting down",
            "question": "Does the computer become very hot, make loud fan noises, or shut down while working?",
            "options": [
                {"text": "Yes, it gets very hot while running", "next": "user-overheat-hot"},
                {"text": "It shuts down unexpectedly after a while", "next": "user-overheat-shutdown"},
            ],
            "is_solution": False,
        },
        "user-overheat-hot": {
            "case_id": "user-overheat-hot",
            "category": "thermal",
            "title": "Device overheating",
            "diagnosis": "Cooling or airflow problem",
            "explanation": "Dust, blocked vents, or a failing fan can make the computer overheat and become unstable.",
            "procedure": "Turn off the computer, unplug it, and clean dust from the vents and fan area with a dry brush or compressed air. Make sure the device has clear airflow. If it still overheats, contact a technician.",
            "warning": "Do not spray liquid into vents or use the computer while it is overheating.",
            "is_solution": True,
        },
        "user-overheat-shutdown": {
            "case_id": "user-overheat-shutdown",
            "category": "thermal",
            "title": "Unexpected shutdown",
            "diagnosis": "The computer is getting too hot",
            "explanation": "A shutdown during use often means the system is protecting itself from heat or a failing cooling system.",
            "procedure": "Let the device cool down before restarting, keep vents clear, and avoid using it on soft surfaces like beds or pillows. Contact a technician if shutdowns continue.",
            "warning": "Do not block air vents or place the device on a blanket or pillow.",
            "is_solution": True,
        },
        "user-slow": {
            "case_id": "user-slow",
            "category": "performance",
            "title": "Slow or freezing computer",
            "question": "Is the computer slow, unresponsive, or freezing during normal use?",
            "options": [
                {"text": "It is slow but still usable", "next": "user-slow-slow"},
                {"text": "It freezes or hangs often", "next": "user-slow-freeze"},
            ],
            "is_solution": False,
        },
        "user-slow-slow": {
            "case_id": "user-slow-slow",
            "category": "performance",
            "title": "Computer running slowly",
            "diagnosis": "Low free storage or too many startup programs",
            "explanation": "A slow computer often has too many programs starting at once or not enough free storage space.",
            "procedure": "Close unnecessary apps, restart the computer, and check if storage is nearly full. Disable non-essential startup programs and remove unneeded files.",
            "warning": "Do not delete files you do not understand or uninstall programs you rely on without checking what they are.",
            "is_solution": True,
        },
        "user-slow-freeze": {
            "case_id": "user-slow-freeze",
            "category": "performance",
            "title": "Freezing computer",
            "diagnosis": "System instability or resource pressure",
            "explanation": "Frequent freezing may come from too many active programs, a failing drive, or a system issue that needs more advanced diagnosis.",
            "procedure": "Restart the computer, close unnecessary programs, and check whether the problem happens after updating or installing software. If freezes continue, contact a technician.",
            "warning": "If the system locks up often and gets hot, do not keep forcing the power button repeatedly.",
            "is_solution": True,
        },
        "user-boot": {
            "case_id": "user-boot",
            "category": "boot",
            "title": "Boot or startup problem",
            "question": "Does the computer start but fail to finish booting or show the login screen?",
            "options": [
                {"text": "It gets stuck before the login screen", "next": "user-boot-stuck"},
                {"text": "It tries to boot but then shows a startup error", "next": "user-boot-error"},
            ],
            "is_solution": False,
        },
        "user-boot-stuck": {
            "case_id": "user-boot-stuck",
            "category": "boot",
            "title": "Startup stuck",
            "diagnosis": "Startup or storage problem",
            "explanation": "A computer that hangs before the login screen may have a storage issue or an operating system problem.",
            "procedure": "Restart the computer and check whether the drive light is active. If the system does not get past startup, contact a technician for further testing.",
            "warning": "Do not repeatedly hard power off the machine while it is trying to boot if it is failing repeatedly.",
            "is_solution": True,
        },
        "user-boot-error": {
            "case_id": "user-boot-error",
            "category": "boot",
            "title": "Startup error",
            "diagnosis": "Operating system or storage problem",
            "explanation": "The computer may be failing to read the system drive or may have a software startup issue.",
            "procedure": "Restart the computer, check the storage drive status, and if it has a recovery option use the built-in startup repair if you are comfortable doing so. Otherwise contact a technician.",
            "warning": "Do not reset the system without backing up important files first.",
            "is_solution": True,
        },
        "user-battery": {
            "case_id": "user-battery",
            "category": "battery",
            "title": "Battery or charging problem",
            "question": "Is the laptop battery not charging, draining quickly, or not detected?",
            "options": [
                {"text": "The battery won't charge", "next": "user-battery-charge"},
                {"text": "The battery drains too quickly", "next": "user-battery-fast"},
                {"text": "The laptop says no charger connected", "next": "user-battery-detect"},
            ],
            "is_solution": False,
        },
        "user-battery-charge": {
            "case_id": "user-battery-charge",
            "category": "battery",
            "title": "Battery not charging",
            "diagnosis": "Charger or battery connection issue",
            "explanation": "If the battery will not charge, the charger, charging port, or battery may be failing.",
            "procedure": "Try a different outlet, check the charger cable for damage, and clean the charging port gently. If charging still fails, contact a technician.",
            "warning": "Do not force the charging cable or use a damaged charger.",
            "is_solution": True,
        },
        "user-battery-fast": {
            "case_id": "user-battery-fast",
            "category": "battery",
            "title": "Battery draining too fast",
            "diagnosis": "Battery health or background usage issue",
            "explanation": "A battery that drains quickly may be worn out or may be affected by background programs and high screen brightness.",
            "procedure": "Lower screen brightness, close unused apps, and check battery usage settings. If battery health is poor, contact a technician or battery service.",
            "warning": "Do not keep using a swollen battery. Stop and seek professional help if it bulges or becomes unusually hot.",
            "is_solution": True,
        },
        "user-battery-detect": {
            "case_id": "user-battery-detect",
            "category": "battery",
            "title": "Laptop not detecting charger",
            "diagnosis": "Charging port or adapter issue",
            "explanation": "The laptop may not be detecting the charger when the port or adapter is not making a clean connection.",
            "procedure": "Check for debris in the charging port, reseat the cable, and try another compatible charger if available. If the problem continues, contact a technician.",
            "warning": "Do not inspect the charging port with metal tools or while the laptop is plugged in.",
            "is_solution": True,
        },
        "user-peripheral": {
            "case_id": "user-peripheral",
            "category": "peripheral",
            "title": "Keyboard, mouse, or USB problem",
            "question": "Is the keyboard, mouse, touchpad, or USB device not responding?",
            "options": [
                {"text": "A USB device is not working", "next": "user-peripheral-usb"},
                {"text": "The keyboard or mouse is not responding", "next": "user-peripheral-input"},
            ],
            "is_solution": False,
        },
        "user-peripheral-usb": {
            "case_id": "user-peripheral-usb",
            "category": "peripheral",
            "title": "USB port problem",
            "diagnosis": "USB connection or driver issue",
            "explanation": "A non-working USB port may be caused by a loose cable, dirt, or a driver issue.",
            "procedure": "Try another USB port, reconnect the device, and restart the computer. If the problem affects several devices, contact a technician.",
            "warning": "Do not force a USB connector into a port if it does not fit or feels jammed.",
            "is_solution": True,
        },
        "user-peripheral-input": {
            "case_id": "user-peripheral-input",
            "category": "peripheral",
            "title": "Input device problem",
            "diagnosis": "Input device or connection issue",
            "explanation": "The keyboard, mouse, or touchpad may not be detected or may have a loose cable or battery issue.",
            "procedure": "Check the battery or connection, reconnect the device, and test another known-good input. If the device still fails, contact a technician.",
            "warning": "Do not open a wireless dongle or keyboard case unless you know how to do so safely.",
            "is_solution": True,
        },
        "user-connectivity": {
            "case_id": "user-connectivity",
            "category": "connectivity",
            "title": "Wi-Fi, Bluetooth, or sound problem",
            "question": "Is the issue with Wi-Fi, Bluetooth, or sound output?",
            "options": [
                {"text": "Wi-Fi or Bluetooth is not working", "next": "user-connectivity-wireless"},
                {"text": "There is no sound or speakers are silent", "next": "user-connectivity-sound"},
            ],
            "is_solution": False,
        },
        "user-connectivity-wireless": {
            "case_id": "user-connectivity-wireless",
            "category": "connectivity",
            "title": "Wireless connection problem",
            "diagnosis": "Wireless connectivity or adapter issue",
            "explanation": "Signal issues can come from a weak connection, adapter settings, or a simple device toggle problem.",
            "procedure": "Toggle Wi-Fi or Bluetooth off and on, confirm the device is within range, and restart the system. If it still fails, contact a technician.",
            "warning": "Do not keep switching wireless radios rapidly if the device is overheating or has poor battery life.",
            "is_solution": True,
        },
        "user-connectivity-sound": {
            "case_id": "user-connectivity-sound",
            "category": "connectivity",
            "title": "No sound or bad audio",
            "diagnosis": "Audio output or driver issue",
            "explanation": "No sound can happen when the output device is unplugged, muted, or not selected properly.",
            "procedure": "Check volume, verify the correct output device is selected, and reconnect speakers or headphones. If sound remains absent, contact a technician.",
            "warning": "Do not force a damaged headphone jack or damaged cable connector.",
            "is_solution": True,
        },
    }

    @classmethod
    def get_all_cases(cls) -> Dict[str, Dict]:
        return dict(cls.CASES)

    @classmethod
    def get_case(cls, case_id: str) -> Optional[Dict]:
        return cls.CASES.get(case_id)

    @classmethod
    def start(cls) -> Dict:
        case = cls.get_case("user-root")
        if not case:
            return {"case_id": "user-root", "audience": "user", "title": "Computer issue", "question": "Describe your problem.", "options": []}
        return {
            "case_id": case["case_id"],
            "audience": "user",
            "category": case["category"],
            "title": case["title"],
            "question": case["question"],
            "options": case.get("options", []),
            "type": "question",
        }

    @classmethod
    def process_step(cls, case_id: str, selected_index: Optional[int] = None) -> Tuple[Dict, str]:
        case = cls.get_case(case_id)
        if not case:
            return {"case_id": case_id, "audience": "user", "diagnosis": "This problem requires a more advanced diagnosis.", "explanation": "This issue is outside the safe Normal User troubleshooting scope. Please contact a technician.", "procedure": "Contact a qualified technician for further diagnosis.", "warning": "Do not perform advanced component repair yourself.", "type": "solution"}, "user-fallback"

        if case.get("is_solution"):
            return {
                "case_id": case["case_id"],
                "audience": "user",
                "category": case["category"],
                "title": case["title"],
                "diagnosis": case.get("diagnosis", case["title"]),
                "explanation": case.get("explanation", "This issue may need a technician."),
                "procedure": case.get("procedure", "Contact a qualified technician."),
                "warning": case.get("warning", "Follow safe steps and seek help if needed."),
                "type": "solution",
            }, case["case_id"]

        if selected_index is None:
            return {
                "case_id": case["case_id"],
                "audience": "user",
                "category": case["category"],
                "title": case["title"],
                "question": case["question"],
                "options": case.get("options", []),
                "type": "question",
            }, case["case_id"]

        options = case.get("options", [])
        if not 0 <= selected_index < len(options):
            return {"case_id": case_id, "audience": "user", "diagnosis": "This problem requires a more advanced diagnosis.", "explanation": "This issue is outside the safe Normal User troubleshooting scope. Please contact a technician.", "procedure": "Contact a qualified technician for further diagnosis.", "warning": "Do not perform advanced component repair yourself.", "type": "solution"}, "user-fallback"

        next_case_id = options[selected_index].get("next")
        next_case = cls.get_case(next_case_id)
        if not next_case:
            return {"case_id": case_id, "audience": "user", "diagnosis": "This problem requires a more advanced diagnosis.", "explanation": "This issue is outside the safe Normal User troubleshooting scope. Please contact a technician.", "procedure": "Contact a qualified technician for further diagnosis.", "warning": "Do not perform advanced component repair yourself.", "type": "solution"}, "user-fallback"

        if next_case.get("is_solution"):
            return {
                "case_id": next_case["case_id"],
                "audience": "user",
                "category": next_case["category"],
                "title": next_case["title"],
                "diagnosis": next_case.get("diagnosis", next_case["title"]),
                "explanation": next_case.get("explanation", "This issue may need a technician."),
                "procedure": next_case.get("procedure", "Contact a qualified technician."),
                "warning": next_case.get("warning", "Follow safe steps and seek help if needed."),
                "type": "solution",
            }, next_case["case_id"]

        return {
            "case_id": next_case["case_id"],
            "audience": "user",
            "category": next_case["category"],
            "title": next_case["title"],
            "question": next_case["question"],
            "options": next_case.get("options", []),
            "type": "question",
        }, next_case["case_id"]


def seed_user_diagnostic_cases():
    """Seed the Normal User knowledge base without altering the Technician KB."""
    for case_id, case_data in UserInferenceEngine.get_all_cases().items():
        NormalUserDiagnosticCase.objects.update_or_create(
            case_id=case_id,
            defaults={
                "category": case_data.get("category", "general"),
                "title": case_data.get("title", case_id),
                "question": case_data.get("question", ""),
                "diagnosis": case_data.get("diagnosis", ""),
                "explanation": case_data.get("explanation", ""),
                "procedure": case_data.get("procedure", ""),
                "warning": case_data.get("warning", ""),
                "option_yes_text": "Yes",
                "option_no_text": "No",
                "next_yes": "",
                "next_no": "",
                "is_root": case_data.get("is_root", False),
                "is_solution": case_data.get("is_solution", False),
            }
        )
    return NormalUserDiagnosticCase.objects.count()
