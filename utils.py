def clamp_channel(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(255, value))


def parse_int(value, default, min_value=None, max_value=None):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default

    if min_value is not None:
        value = max(min_value, value)
    if max_value is not None:
        value = min(max_value, value)

    return value


def parse_hex_color(value, default=(255, 255, 255)):
    if not isinstance(value, str):
        return default

    text = value.strip().lstrip("#")
    if len(text) != 6:
        return default

    try:
        return (
            int(text[0:2], 16),
            int(text[2:4], 16),
            int(text[4:6], 16),
        )
    except ValueError:
        return default


def parse_color(query, default=(255, 255, 255)):
    if "hex" in query:
        parsed = parse_hex_color(query["hex"], None)
        if parsed is not None:
            return parsed

    return (
        clamp_channel(query.get("r", default[0])),
        clamp_channel(query.get("g", default[1])),
        clamp_channel(query.get("b", default[2])),
    )


def parse_color_value(value, default=(255, 255, 255)):
    if isinstance(value, str):
        parsed = parse_hex_color(value, None)
        if parsed is not None:
            return parsed

        lowered = value.strip().lower()
        if lowered in ("0", "off", "black"):
            return (0, 0, 0)
        if lowered in ("1", "on"):
            return default

    if isinstance(value, dict):
        return (
            clamp_channel(value.get("r", default[0])),
            clamp_channel(value.get("g", default[1])),
            clamp_channel(value.get("b", default[2])),
        )

    if isinstance(value, list) or isinstance(value, tuple):
        return (
            clamp_channel(value[0] if len(value) > 0 else default[0]),
            clamp_channel(value[1] if len(value) > 1 else default[1]),
            clamp_channel(value[2] if len(value) > 2 else default[2]),
        )

    return default


def parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0

    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False

    return default


def parse_query(query_string):
    result = {}
    if not query_string:
        return result

    for part in query_string.split("&"):
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
        else:
            key, value = part, ""
        result[url_decode(key)] = url_decode(value)
    return result


def url_decode(value):
    value = value.replace("+", " ")
    output = ""
    index = 0

    while index < len(value):
        if value[index] == "%" and index + 2 < len(value):
            try:
                output += chr(int(value[index + 1:index + 3], 16))
                index += 3
                continue
            except ValueError:
                pass
        output += value[index]
        index += 1

    return output
