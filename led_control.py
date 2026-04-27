import uasyncio as asyncio
import ujson
from machine import Pin
from neopixel import NeoPixel
from urandom import getrandbits

from config import (
    AUX_LED_PIN,
    BUTTON_PIN,
    MAX_STEP_MS,
    MIN_STEP_MS,
    STATE_FILE,
    ZONE_NAMES,
    ZONES,
)
from patterns import named_pattern_steps, normalize_steps, scale_color, serialize_steps
from utils import clamp_channel, parse_bool, parse_int


# Reserved for the second RGB SK6812 LED. It is intentionally not bound to
# windows/signs until the final wiring is known.
aux_led = NeoPixel(Pin(AUX_LED_PIN, Pin.OUT), 1)

# Most simple button modules pull the pin to GND when pressed.
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)


class LedController:
    def __init__(self, zone_name, pixels, pixel_count):
        self.zone_name = zone_name
        self.pixels = pixels
        self.pixel_count = pixel_count
        self.color = (255, 255, 255)
        self.mode = "off"
        self.pattern = "none"
        self.interval_ms = 500
        self.repeat = True
        self.custom_steps = None
        self._task = None
        self._is_on = False
        self._current_color = (0, 0, 0)
        self._write((0, 0, 0))

    def _write(self, color):
        for index in range(self.pixel_count):
            self.pixels[index] = color
        self.pixels.write()
        self._is_on = color != (0, 0, 0)
        self._current_color = color

    def _cancel_animation(self):
        if self._task:
            self._task.cancel()
            self._task = None

    def off(self):
        self._cancel_animation()
        self.mode = "off"
        self.pattern = "none"
        self.repeat = True
        self.custom_steps = None
        self._write((0, 0, 0))

    def on(self, color=None):
        self._cancel_animation()
        if color is not None:
            self.color = color
        self.mode = "solid"
        self.pattern = "none"
        self.repeat = True
        self.custom_steps = None
        self._write(self.color)

    def blink(self, color=None, interval_ms=500):
        self._cancel_animation()
        if color is not None:
            self.color = color
        self.interval_ms = parse_int(interval_ms, 500, 50, 10000)
        self.mode = "blink"
        self.pattern = "blink"
        self.repeat = True
        self.custom_steps = None
        self._task = asyncio.create_task(self._blink_loop())

    def pulse(self, color=None, period_ms=1500):
        self._cancel_animation()
        if color is not None:
            self.color = color
        self.interval_ms = parse_int(period_ms, 1500, 300, 10000)
        self.mode = "pulse"
        self.pattern = "pulse"
        self.repeat = True
        self.custom_steps = None
        self._task = asyncio.create_task(self._pulse_loop())

    def pattern_flash(self, color=None):
        if color is not None:
            self.color = color
        self.pattern_sequence("flash", named_pattern_steps("flash", self.color))

    def pattern_heartbeat(self, color=None):
        if color is not None:
            self.color = color
        self.pattern_sequence("heartbeat", named_pattern_steps("heartbeat", self.color))

    def pattern_sequence(self, name, steps, color=None, interval_ms=None):
        if color is not None:
            self.color = color
        if interval_ms is not None:
            self.interval_ms = parse_int(interval_ms, self.interval_ms, MIN_STEP_MS, MAX_STEP_MS)
        self.run_sequence(name, steps, True, "pattern", None)

    def pattern_glitch(self, color=None, interval_ms=None):
        self._cancel_animation()
        if color is not None:
            self.color = color
        if interval_ms is not None:
            self.interval_ms = parse_int(interval_ms, self.interval_ms, MIN_STEP_MS, MAX_STEP_MS)
        self.mode = "pattern"
        self.pattern = "glitch"
        self.repeat = True
        self.custom_steps = None
        self._task = asyncio.create_task(self._glitch_loop())

    def custom_sequence(self, steps, repeat=True, name="custom"):
        self.run_sequence(name, steps, repeat, "custom", steps)

    def run_sequence(self, name, steps, repeat=True, mode="custom", custom_steps=None):
        self._cancel_animation()
        for step in steps:
            if step["color"] != (0, 0, 0):
                self.color = step["color"]
                break
        self.mode = mode
        self.pattern = name
        self.repeat = repeat
        self.custom_steps = custom_steps
        self._task = asyncio.create_task(self._sequence_loop(steps, repeat))

    async def _blink_loop(self):
        try:
            while True:
                self._write(self.color)
                await asyncio.sleep_ms(self.interval_ms)
                self._write((0, 0, 0))
                await asyncio.sleep_ms(self.interval_ms)
        except asyncio.CancelledError:
            raise

    async def _pulse_loop(self):
        steps = 24
        pause_ms = max(10, self.interval_ms // (steps * 2))

        try:
            while True:
                for step in range(steps + 1):
                    self._write(scale_color(self.color, step / steps))
                    await asyncio.sleep_ms(pause_ms)
                for step in range(steps - 1, -1, -1):
                    self._write(scale_color(self.color, step / steps))
                    await asyncio.sleep_ms(pause_ms)
        except asyncio.CancelledError:
            raise

    async def _fade_to(self, target, ms):
        start = self._current_color
        steps = max(1, min(32, ms // 30))
        pause_ms = max(1, ms // steps)

        for index in range(1, steps + 1):
            self._write((
                start[0] + ((target[0] - start[0]) * index) // steps,
                start[1] + ((target[1] - start[1]) * index) // steps,
                start[2] + ((target[2] - start[2]) * index) // steps,
            ))
            await asyncio.sleep_ms(pause_ms)

    async def _sequence_loop(self, steps, repeat):
        try:
            while True:
                for step in steps:
                    color = step["color"]
                    ms = step["ms"]
                    if step.get("fade", False):
                        await self._fade_to(color, ms)
                    else:
                        self._write(color)
                        await asyncio.sleep_ms(ms)

                if not repeat:
                    break
        except asyncio.CancelledError:
            raise

    async def _glitch_loop(self):
        try:
            while True:
                self._write(self.color)
                await asyncio.sleep_ms(900 + getrandbits(9))

                flickers = 2 + (getrandbits(2) % 4)
                for _ in range(flickers):
                    event = getrandbits(3)

                    if event <= 2:
                        self._write((0, 0, 0))
                    elif event <= 5:
                        self._write(scale_color(self.color, 0.18 + ((getrandbits(3) + 1) / 12)))
                    else:
                        self._write((255, 255, 255))

                    await asyncio.sleep_ms(20 + (getrandbits(5) * 3))
                    self._write(self.color)
                    await asyncio.sleep_ms(25 + (getrandbits(5) * 4))
        except asyncio.CancelledError:
            raise

    def state(self):
        config = ZONES[self.zone_name]
        return {
            "zone": self.zone_name,
            "label": config["label"],
            "enabled": True,
            "ready": True,
            "draft": config["draft"],
            "pin": config["pin"],
            "pixel_count": self.pixel_count,
            "mode": self.mode,
            "pattern": self.pattern,
            "color": {
                "r": self.color[0],
                "g": self.color[1],
                "b": self.color[2],
            },
            "interval_ms": self.interval_ms,
            "repeat": self.repeat,
            "step_count": len(self.custom_steps) if self.custom_steps else 0,
            "is_on": self._is_on,
        }


def make_disabled_zone_state(zone_name):
    config = ZONES[zone_name]
    return {
        "zone": zone_name,
        "label": config["label"],
        "enabled": False,
        "ready": False,
        "draft": config["draft"],
        "pin": config["pin"],
        "pixel_count": config["pixel_count"],
        "mode": "disabled",
        "pattern": "none",
        "color": {"r": 0, "g": 0, "b": 0},
        "interval_ms": 0,
        "repeat": False,
        "step_count": 0,
        "is_on": False,
    }


def create_enabled_controllers():
    controllers = {}

    for zone_name in ZONE_NAMES:
        config = ZONES[zone_name]
        if not config["enabled"]:
            continue

        pin = config["pin"]
        if pin is None:
            continue

        pixels = NeoPixel(Pin(pin, Pin.OUT), config["pixel_count"])
        controllers[zone_name] = LedController(zone_name, pixels, config["pixel_count"])

    return controllers


zone_controllers = create_enabled_controllers()


def get_zone(zone_name):
    return zone_controllers.get(zone_name)


def zone_exists(zone_name):
    return zone_name in ZONES


def zone_enabled(zone_name):
    return bool(ZONES[zone_name]["enabled"]) if zone_exists(zone_name) else False


def zone_state(zone_name):
    controller = get_zone(zone_name)
    if controller:
        return controller.state()
    return make_disabled_zone_state(zone_name)


def all_zones_state():
    zones = {}
    for zone_name in ZONE_NAMES:
        zones[zone_name] = zone_state(zone_name)

    return {
        "zones": zones,
        "zone_order": list(ZONE_NAMES),
        "button_pressed": button.value() == 0,
        "aux_led_ready": True,
    }


def apply_named_pattern(controller, name, color, query=None):
    query = query or {}
    if name == "glitch":
        interval_ms = parse_int(query.get("interval", query.get("period", controller.interval_ms)), controller.interval_ms, MIN_STEP_MS, MAX_STEP_MS)
        controller.pattern_glitch(color, interval_ms)
        return True

    steps = named_pattern_steps(name, color, query)
    if steps is None:
        return False

    interval_ms = parse_int(query.get("interval", query.get("period", controller.interval_ms)), controller.interval_ms, MIN_STEP_MS, MAX_STEP_MS)
    controller.pattern_sequence(name, steps, color, interval_ms)
    return True


def serialize_controller_state(controller):
    data = {
        "mode": controller.mode,
        "pattern": controller.pattern,
        "color": [controller.color[0], controller.color[1], controller.color[2]],
        "interval_ms": controller.interval_ms,
        "repeat": controller.repeat,
    }

    if controller.mode == "custom" and controller.custom_steps:
        data["steps"] = serialize_steps(controller.custom_steps)

    return data


def save_led_state():
    data = {"zones": {}}

    for zone_name in ZONE_NAMES:
        controller = get_zone(zone_name)
        if controller:
            data["zones"][zone_name] = serialize_controller_state(controller)

    try:
        with open(STATE_FILE, "w") as file:
            file.write(ujson.dumps(data))
    except OSError as exc:
        print("State save failed:", exc)


def load_led_state():
    try:
        with open(STATE_FILE, "r") as file:
            return ujson.loads(file.read())
    except (OSError, ValueError) as exc:
        print("State load skipped:", exc)
        return None


def state_color(data):
    color = data.get("color", [255, 255, 255])
    if not isinstance(color, list) and not isinstance(color, tuple):
        return (255, 255, 255)

    return (
        clamp_channel(color[0] if len(color) > 0 else 255),
        clamp_channel(color[1] if len(color) > 1 else 255),
        clamp_channel(color[2] if len(color) > 2 else 255),
    )


def restore_controller_state(controller, data):
    if not data or not hasattr(data, "get"):
        controller.off()
        return

    mode = data.get("mode", "off")
    pattern = data.get("pattern", "none")
    color = state_color(data)
    interval_ms = parse_int(data.get("interval_ms", 500), 500, 50, 10000)

    if mode == "solid":
        controller.on(color)
    elif mode == "blink":
        controller.blink(color, interval_ms)
    elif mode == "pulse":
        controller.pulse(color, interval_ms)
    elif mode == "pattern" and apply_named_pattern(controller, pattern, color, {"interval": interval_ms}):
        return
    elif mode == "custom" and "steps" in data:
        try:
            steps = normalize_steps(data.get("steps"), color)
            controller.custom_sequence(steps, parse_bool(data.get("repeat"), True), pattern)
        except ValueError as exc:
            print("State restore failed:", exc)
            controller.off()
    else:
        controller.off()


def restore_led_state(data):
    if not data or not hasattr(data, "get"):
        for controller in zone_controllers.values():
            controller.off()
        return

    saved_zones = data.get("zones")
    if not isinstance(saved_zones, dict):
        saved_zones = {"lamp": data}

    for zone_name, controller in zone_controllers.items():
        restore_controller_state(controller, saved_zones.get(zone_name))
