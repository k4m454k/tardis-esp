import ujson

from config import MAX_PATTERN_STEPS, MAX_STEP_MS, MIN_STEP_MS
from utils import parse_bool, parse_color_value, parse_hex_color, parse_int


def scale_color(color, brightness):
    return (
        int(color[0] * brightness),
        int(color[1] * brightness),
        int(color[2] * brightness),
    )


def make_step(color, ms, fade=False):
    return {
        "color": parse_color_value(color, (0, 0, 0)),
        "ms": parse_int(ms, 100, MIN_STEP_MS, MAX_STEP_MS),
        "fade": bool(fade),
    }


def color_step(color, ms, brightness=1, fade=False):
    return make_step(scale_color(color, brightness), ms, fade)


def off_step(ms, fade=False):
    return make_step((0, 0, 0), ms, fade)


def serialize_steps(steps):
    serialized = []

    for step in steps:
        color = step["color"]
        serialized.append({
            "color": [color[0], color[1], color[2]],
            "ms": step["ms"],
            "fade": step.get("fade", False),
        })

    return serialized


def normalize_steps(raw_steps, base_color):
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("steps must be a non-empty list")
    if len(raw_steps) > MAX_PATTERN_STEPS:
        raise ValueError("too many steps")

    steps = []

    for raw in raw_steps:
        if not isinstance(raw, dict):
            raise ValueError("each step must be an object")

        ms = parse_int(raw.get("ms", raw.get("duration", 100)), 100, MIN_STEP_MS, MAX_STEP_MS)
        fade = parse_bool(raw.get("fade"), False)

        if "color" in raw:
            color = parse_color_value(raw.get("color"), base_color)
        elif "hex" in raw:
            color = parse_hex_color(raw.get("hex"), base_color)
        elif "on" in raw:
            color = base_color if parse_bool(raw.get("on"), True) else (0, 0, 0)
        else:
            color = base_color

        steps.append(make_step(color, ms, fade))

    return steps


def steps_from_text(pattern, base_color, unit_ms=150):
    pattern = pattern.strip()
    if not pattern:
        raise ValueError("pattern is empty")

    unit_ms = parse_int(unit_ms, 150, MIN_STEP_MS, MAX_STEP_MS)

    if all(char in "01" for char in pattern):
        if len(pattern) > MAX_PATTERN_STEPS:
            raise ValueError("too many steps")
        return [
            make_step(base_color if char == "1" else (0, 0, 0), unit_ms)
            for char in pattern
        ]

    tokens = [token.strip() for token in pattern.replace(";", ",").split(",") if token.strip()]
    if not tokens:
        raise ValueError("pattern is empty")
    if len(tokens) > MAX_PATTERN_STEPS:
        raise ValueError("too many steps")

    steps = []

    for token in tokens:
        parts = [part.strip() for part in token.split(":")]
        color = parse_color_value(parts[0], base_color)
        ms = parse_int(parts[1] if len(parts) > 1 else unit_ms, unit_ms, MIN_STEP_MS, MAX_STEP_MS)
        fade = len(parts) > 2 and (parts[2].lower() == "fade" or parse_bool(parts[2], False))
        steps.append(make_step(color, ms, fade))

    return steps


def custom_steps_from_json(body):
    try:
        data = ujson.loads(body)
    except ValueError:
        raise ValueError("invalid JSON")

    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")

    base_color = parse_color_value(data.get("color", data.get("hex", "#ffffff")), (255, 255, 255))
    return (
        normalize_steps(data.get("steps"), base_color),
        parse_bool(data.get("repeat"), True),
        str(data.get("name", "custom"))[:24],
    )


def named_pattern_steps(name, color, query=None):
    query = query or {}
    name = name.strip().lower()
    interval_ms = parse_int(query.get("interval", query.get("period", 500)), 500, MIN_STEP_MS, MAX_STEP_MS)

    if name == "flash":
        return [
            color_step(color, 80), off_step(120),
            color_step(color, 80), off_step(120),
            color_step(color, 80), off_step(900),
        ]

    if name == "heartbeat":
        return [
            color_step(color, 90), off_step(120),
            color_step(color, 120), off_step(820),
        ]

    if name == "double":
        return [
            color_step(color, 120), off_step(120),
            color_step(color, 120), off_step(760),
        ]

    if name == "triple":
        return [
            color_step(color, 80), off_step(110),
            color_step(color, 80), off_step(110),
            color_step(color, 80), off_step(760),
        ]

    if name == "sos":
        return [
            color_step(color, 120), off_step(120),
            color_step(color, 120), off_step(120),
            color_step(color, 120), off_step(240),
            color_step(color, 360), off_step(120),
            color_step(color, 360), off_step(120),
            color_step(color, 360), off_step(240),
            color_step(color, 120), off_step(120),
            color_step(color, 120), off_step(120),
            color_step(color, 120), off_step(1100),
        ]

    if name == "breathe":
        return [
            color_step(color, interval_ms, 1, True),
            color_step(color, interval_ms // 4),
            off_step(interval_ms, True),
            off_step(interval_ms // 3),
        ]

    if name == "flicker":
        return [
            color_step(color, 60, .35),
            color_step(color, 45, .95),
            color_step(color, 80, .50),
            color_step(color, 40, .80),
            color_step(color, 90, .25),
            color_step(color, 50, 1),
            color_step(color, 500, .55),
        ]

    if name == "alarm":
        return [color_step(color, 180), off_step(180)]

    if name == "notify":
        return [
            color_step(color, 80), off_step(100),
            color_step(color, 80), off_step(380),
            color_step(color, 650, .28, True),
            off_step(650, True),
        ]

    if name == "rainbow":
        return [
            make_step("#ff0000", interval_ms, True),
            make_step("#ff7a00", interval_ms, True),
            make_step("#ffe600", interval_ms, True),
            make_step("#00d26a", interval_ms, True),
            make_step("#00a3ff", interval_ms, True),
            make_step("#9b5cff", interval_ms, True),
        ]

    if name == "wifi":
        return [
            make_step("#ff0000", 120), off_step(160),
            make_step("#ff0000", 120), off_step(650),
        ]

    return None
