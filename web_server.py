import uasyncio as asyncio
import gc
import os
import ujson

from config import HTTP_HOST, HTTP_PORT, MAX_BODY_BYTES
from led_control import (
    all_zones_state,
    apply_named_pattern,
    get_zone,
    save_led_state,
    zone_enabled,
    zone_exists,
    zone_state,
)
from patterns import custom_steps_from_json, steps_from_text
from utils import parse_bool, parse_color, parse_int, parse_query


FILE_CHUNK_BYTES = 1024
GC_MAINTENANCE_SECONDS = 60
CONNECTION_ERROR_CODES = (32, 104, 113, 128)
INTERNAL_ERROR_BODY = b'{"error":"Internal server error"}'
MEMORY_ERROR_BODY = b'{"error":"Memory allocation failed"}'


def status_reason(status):
    return {
        200: "OK",
        400: "Bad Request",
        404: "Not Found",
        500: "Internal Server Error",
    }.get(status, "OK")


def response_headers(status, content_type, content_length):
    return (
        "HTTP/1.1 {} {}\r\n"
        "Content-Type: {}\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
        "Access-Control-Allow-Headers: Content-Type\r\n"
        "\r\n"
    ).format(status, status_reason(status), content_type, content_length).encode()


def response(status, content_type, body):
    if isinstance(body, str):
        body = body.encode()

    return ("bytes", status, content_type, body)


def json_response(data, status=200):
    return response(status, "application/json", ujson.dumps(data))


def file_response(path, content_type):
    try:
        return ("file", 200, content_type, path, os.stat(path)[6])
    except OSError:
        return response(
            500,
            "text/plain; charset=utf-8",
            "Missing {}. Upload it next to main.py.".format(path),
        )


def memory_free():
    return gc.mem_free() if hasattr(gc, "mem_free") else None


def memory_allocated():
    return gc.mem_alloc() if hasattr(gc, "mem_alloc") else None


def memory_state():
    return {
        "free": memory_free(),
        "allocated": memory_allocated(),
    }


def is_connection_error(exc):
    return isinstance(exc, OSError) and exc.args and exc.args[0] in CONNECTION_ERROR_CODES


def zone_error_or_controller(zone_name, require_enabled=True):
    if not zone_exists(zone_name):
        return None, json_response({"error": "Unknown zone"}, 404)

    if require_enabled and not zone_enabled(zone_name):
        return None, json_response({"error": "Zone is disabled"}, 400)

    controller = get_zone(zone_name)
    if require_enabled and controller is None:
        return None, json_response({"error": "Zone is not ready"}, 400)

    return controller, None


def handle_zone_action(method, zone_name, action, query, body):
    if action == "state":
        if not zone_exists(zone_name):
            return json_response({"error": "Unknown zone"}, 404)
        return json_response(zone_state(zone_name))

    controller, error = zone_error_or_controller(zone_name)
    if error:
        return error

    if action == "off":
        controller.off()
        save_led_state()
        return json_response(controller.state())

    if action == "on":
        controller.on(parse_color(query, controller.color))
        save_led_state()
        return json_response(controller.state())

    if action == "color":
        controller.on(parse_color(query, controller.color))
        save_led_state()
        return json_response(controller.state())

    if action == "blink":
        interval_ms = query.get("interval", query.get("interval_ms", 500))
        controller.blink(parse_color(query, controller.color), parse_int(interval_ms, 500, 50, 10000))
        save_led_state()
        return json_response(controller.state())

    if action == "pulse":
        period_ms = query.get("period", query.get("period_ms", 1500))
        controller.pulse(parse_color(query, controller.color), period_ms)
        save_led_state()
        return json_response(controller.state())

    if action == "pattern":
        if method != "GET":
            return json_response({"error": "Use GET for named patterns"}, 400)

        pattern = query.get("name", "flash")
        color = parse_color(query, controller.color)
        if not apply_named_pattern(controller, pattern, color, query):
            return json_response({"error": "Unknown pattern"}, 400)
        save_led_state()
        return json_response(controller.state())

    if action == "custom":
        try:
            if method == "POST":
                if not body:
                    return json_response({"error": "Missing JSON body"}, 400)
                steps, repeat, name = custom_steps_from_json(body.decode())
            else:
                if "pattern" not in query:
                    return json_response({"error": "Missing pattern"}, 400)
                color = parse_color(query, controller.color)
                steps = steps_from_text(
                    query.get("pattern", ""),
                    color,
                    query.get("unit", query.get("interval", 150)),
                )
                repeat = parse_bool(query.get("repeat"), True)
                name = query.get("name", "custom")[:24]

            controller.custom_sequence(steps, repeat, name)
            save_led_state()
            return json_response(controller.state())
        except ValueError as exc:
            return json_response({"error": str(exc)}, 400)

    return json_response({"error": "Not found"}, 404)


def route(method, target, body=b""):
    path, _, query_string = target.partition("?")
    query = parse_query(query_string)

    if method == "OPTIONS":
        return json_response({"ok": True})

    if method not in ("GET", "POST"):
        return json_response({"error": "Only GET and POST are supported"}, 400)

    if path == "/":
        return file_response("index.html", "text/html; charset=utf-8")

    if path == "/api/zones":
        return json_response(all_zones_state())

    if path == "/api/system":
        gc.collect()
        return json_response({
            "memory": memory_state(),
            "gc": {
                "file_chunk_bytes": FILE_CHUNK_BYTES,
                "maintenance_seconds": GC_MAINTENANCE_SECONDS,
            },
        })

    parts = path.strip("/").split("/")
    if len(parts) == 4 and parts[0] == "api" and parts[1] == "zones":
        return handle_zone_action(method, parts[2], parts[3], query, body)

    return json_response({"error": "Not found"}, 404)


async def send_response(writer, payload):
    response_type = payload[0]

    if response_type == "file":
        _, status, content_type, path, content_length = payload
        gc.collect()
        writer.write(response_headers(status, content_type, content_length))
        await writer.drain()

        with open(path, "rb") as file:
            while True:
                chunk = file.read(FILE_CHUNK_BYTES)
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()
        return

    _, status, content_type, body = payload
    writer.write(response_headers(status, content_type, len(body)))
    writer.write(body)
    await writer.drain()


async def send_static_error(writer, status, body):
    try:
        writer.write(response_headers(status, "application/json", len(body)))
        writer.write(body)
        await writer.drain()
    except OSError as exc:
        if not is_connection_error(exc):
            print("HTTP error response failed:", exc)
    except Exception as exc:
        print("HTTP error response failed:", exc)


async def handle_client(reader, writer):
    try:
        request_line = await reader.readline()
        if not request_line:
            return

        parts = request_line.decode().strip().split()
        headers = {}
        while True:
            header = await reader.readline()
            if not header or header == b"\r\n":
                break
            header = header.decode().strip()
            if ":" in header:
                key, value = header.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        content_length = parse_int(headers.get("content-length", 0), 0, 0, MAX_BODY_BYTES + 1)
        body = b""

        if content_length > MAX_BODY_BYTES:
            payload = json_response({"error": "Request body is too large"}, 400)
        else:
            while len(body) < content_length:
                chunk = await reader.read(content_length - len(body))
                if not chunk:
                    break
                body += chunk

            if len(parts) < 2:
                payload = json_response({"error": "Bad request"}, 400)
            else:
                payload = route(parts[0], parts[1], body)

        await send_response(writer, payload)
    except OSError as exc:
        if not is_connection_error(exc):
            print("HTTP socket error:", exc)
            await send_static_error(writer, 500, INTERNAL_ERROR_BODY)
    except MemoryError as exc:
        gc.collect()
        print("HTTP memory error:", exc, "free:", memory_free(), "allocated:", memory_allocated())
        await send_static_error(writer, 500, MEMORY_ERROR_BODY)
    except Exception as exc:
        print("HTTP error:", exc)
        await send_static_error(writer, 500, INTERNAL_ERROR_BODY)
    finally:
        await close_writer(writer)
        gc.collect()


async def close_writer(writer):
    try:
        if hasattr(writer, "aclose"):
            await writer.aclose()
            return

        writer.close()
        if hasattr(writer, "wait_closed"):
            await writer.wait_closed()
    except OSError as exc:
        if not is_connection_error(exc):
            print("HTTP close failed:", exc)
    except Exception as exc:
        print("HTTP close failed:", exc)


async def gc_maintenance_loop():
    while True:
        await asyncio.sleep(GC_MAINTENANCE_SECONDS)
        gc.collect()


async def start_http_server(wlan):
    asyncio.create_task(gc_maintenance_loop())
    await asyncio.start_server(handle_client, HTTP_HOST, HTTP_PORT)
    print("HTTP server listening on http://{}:{}/".format(wlan.ifconfig()[0], HTTP_PORT))

    while True:
        await asyncio.sleep(3600)
