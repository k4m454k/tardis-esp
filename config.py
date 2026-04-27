WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
DEVICE_HOSTNAME = "tardis-esp"

HTTP_HOST = "0.0.0.0"
HTTP_PORT = 80

AUX_LED_PIN = 2
BUTTON_PIN = 3

ZONE_NAMES = ("lamp", "windows", "signs")
ZONES = {
    "lamp": {
        "label": "Top lamp",
        "enabled": True,
        "pin": 10,
        "pixel_count": 1,
        "draft": False,
    },
    "windows": {
        "label": "Windows",
        "enabled": True,
        "pin": 8,
        "pixel_count": 3,
        "draft": False,
    },
    "signs": {
        "label": "Police box signs",
        "enabled": True,
        "pin": 7,
        "pixel_count": 3,
        "draft": False,
    },
}

STATE_FILE = "led_state.json"

MAX_BODY_BYTES = 2048
MAX_PATTERN_STEPS = 32
MIN_STEP_MS = 20
MAX_STEP_MS = 10000
