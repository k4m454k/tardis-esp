# TARDIS ESP Light Zones API

ESP32-C3 runs a small HTTP server on port `80`.

Default base URL:

```text
http://tardis-esp.local
```

If `.local` is not available, use the IP printed in the serial console:

```text
HTTP server listening on http://<ip>:80/
```

The public API is zone-only. The configured zones are `lamp`, `windows`, and `signs`.

## Zones

| Zone | Meaning | Enabled | Pin | Pixels |
| --- | --- | --- | --- | --- |
| `lamp` | Top lamp | yes | `GPIO10` | `1` |
| `windows` | TARDIS windows | yes | `GPIO8` | `3` |
| `signs` | `POLICE PUBLIC CALL BOX` signs | yes | `GPIO7` | `3` |

If a zone is disabled in `config.py`, it does not create a `Pin`/`NeoPixel` object. Control endpoints for disabled zones return:

```json
{
  "error": "Zone is disabled"
}
```

with HTTP `400`.

## State Shape

`GET /api/zones` returns all zones plus shared hardware state:

```json
{
  "zones": {
    "lamp": {
      "zone": "lamp",
      "label": "Top lamp",
      "enabled": true,
      "ready": true,
      "draft": false,
      "pin": 10,
      "pixel_count": 1,
      "mode": "pattern",
      "pattern": "heartbeat",
      "color": { "r": 255, "g": 0, "b": 0 },
      "interval_ms": 500,
      "repeat": true,
      "step_count": 0,
      "is_on": true
    },
    "windows": {
      "zone": "windows",
      "label": "Windows",
      "enabled": true,
      "ready": true,
      "draft": false,
      "pin": 8,
      "pixel_count": 3,
      "mode": "off",
      "pattern": "none",
      "color": { "r": 255, "g": 255, "b": 255 },
      "interval_ms": 500,
      "repeat": true,
      "step_count": 0,
      "is_on": false
    }
  },
  "zone_order": ["lamp", "windows", "signs"],
  "button_pressed": false,
  "aux_led_ready": true
}
```

`GET /api/zones/{zone}/state` returns one zone object.

Zone fields:

| Field | Type | Description |
| --- | --- | --- |
| `zone` | string | Zone slug: `lamp`, `windows`, or `signs`. |
| `label` | string | Human-readable zone label. |
| `enabled` | boolean | Whether firmware should create hardware objects and allow control. |
| `ready` | boolean | Whether the zone has an initialized `NeoPixel` object. |
| `draft` | boolean | Whether the zone is preconfigured but not finalized. |
| `pin` | integer or null | GPIO pin, or `null` for disabled draft zones. |
| `pixel_count` | integer | Number of pixels in the zone chain. |
| `mode` | string | `off`, `solid`, `blink`, `pulse`, `pattern`, `custom`, or `disabled`. |
| `pattern` | string | Current pattern name. |
| `color` | object | Last active RGB color. |
| `interval_ms` | integer | Current speed/period value. |
| `repeat` | boolean | Whether the active sequence repeats. |
| `step_count` | integer | Number of custom sequence steps. |
| `is_on` | boolean | Whether the zone is currently lit at this exact moment. |

## Color Parameters

Most control endpoints accept either:

```text
hex=ff0000
```

or separate RGB channels:

```text
r=255&g=0&b=0
```

Rules:

- `hex` may include or omit `#`, but URL examples omit it.
- `r`, `g`, and `b` are clamped to `0..255`.
- If no color is provided, the current stored zone color is reused.

## Endpoints

### `GET /`

Returns the web UI from `index.html`.

### `GET /api/zones`

Returns every configured zone.

Example:

```sh
curl http://tardis-esp.local/api/zones
```

### `GET /api/zones/{zone}/state`

Returns state for one zone.

Example:

```sh
curl http://tardis-esp.local/api/zones/lamp/state
```

### `GET /api/zones/{zone}/off`

Turns an enabled zone off and saves state.

Example:

```sh
curl http://tardis-esp.local/api/zones/lamp/off
```

### `GET /api/zones/{zone}/on`

Turns an enabled zone on with a solid color and saves state.

Examples:

```sh
curl "http://tardis-esp.local/api/zones/lamp/on?hex=ffffff"
curl "http://tardis-esp.local/api/zones/lamp/on?r=255&g=64&b=0"
```

### `GET /api/zones/{zone}/color`

Alias for setting a solid color. Saves state.

Example:

```sh
curl "http://tardis-esp.local/api/zones/lamp/color?hex=00a3ff"
```

### `GET /api/zones/{zone}/blink`

Starts a simple on/off blink loop and saves state.

Query parameters:

| Parameter | Required | Description |
| --- | --- | --- |
| `hex` or `r/g/b` | no | Blink color. |
| `interval` | no | On/off duration in ms. Default `500`. |
| `interval_ms` | no | Alias for `interval`. |

Example:

```sh
curl "http://tardis-esp.local/api/zones/lamp/blink?hex=ff0000&interval=300"
```

### `GET /api/zones/{zone}/pulse`

Starts a smooth pulse loop and saves state.

Query parameters:

| Parameter | Required | Description |
| --- | --- | --- |
| `hex` or `r/g/b` | no | Pulse color. |
| `period` | no | Pulse period in ms. Default `1500`. |
| `period_ms` | no | Alias for `period`. |

Example:

```sh
curl "http://tardis-esp.local/api/zones/lamp/pulse?hex=00a3ff&period=1500"
```

### `GET /api/zones/{zone}/pattern`

Starts a named built-in pattern and saves state.

Query parameters:

| Parameter | Required | Description |
| --- | --- | --- |
| `name` | no | Pattern name. Default `flash`. |
| `hex` or `r/g/b` | no | Pattern color. Ignored by `rainbow`. |
| `interval` | no | Speed value used by `breathe` and `rainbow`. Default `500`. |
| `period` | no | Alias for `interval`. |

Supported names:

`flash`, `heartbeat`, `double`, `triple`, `sos`, `breathe`, `flicker`, `glitch`, `alarm`, `notify`, `rainbow`, `wifi`.

`glitch` keeps the zone lit with the selected color and occasionally adds short random flickers, dim drops, full cut-outs, and brief white spikes.

Examples:

```sh
curl "http://tardis-esp.local/api/zones/lamp/pattern?name=heartbeat&hex=ff0000"
curl "http://tardis-esp.local/api/zones/lamp/pattern?name=rainbow&interval=700"
```

### `GET /api/zones/{zone}/custom`

Starts a custom pattern from a compact query-string format and saves it.

Query parameters:

| Parameter | Required | Description |
| --- | --- | --- |
| `pattern` | yes | Compact pattern string. |
| `hex` or `r/g/b` | no | Base color. Default is current zone color. |
| `unit` | no | Duration in ms for binary pattern characters. Default `150`. |
| `interval` | no | Alias for `unit`. |
| `repeat` | no | `1`, `0`, `true`, `false`, `yes`, `no`, `on`, or `off`. Default `true`. |
| `name` | no | Custom pattern name stored in state. Default `custom`. |

Binary form:

```text
100101110
```

Each `1` means base color for `unit` ms. Each `0` means off for `unit` ms.

Timed form:

```text
1:120,0:120,1:120,0:800
```

Timed token format:

```text
color_or_state:duration_ms[:fade]
```

Supported `color_or_state` values:

- `1` or `on`: base color.
- `0`, `off`, or `black`: off.
- `ff0000` or `#ff0000`: explicit color.

Examples:

```sh
curl "http://tardis-esp.local/api/zones/lamp/custom?hex=ff0000&unit=150&pattern=100101110"
curl "http://tardis-esp.local/api/zones/lamp/custom?hex=00a3ff&pattern=1:120,0:120,1:120,0:800&name=double-custom"
curl "http://tardis-esp.local/api/zones/lamp/custom?pattern=ff0000:300:fade,000000:300:fade&repeat=true"
```

### `POST /api/zones/{zone}/custom`

Starts a custom pattern from JSON and saves it.

Limits:

- request body: max `2048` bytes;
- steps: max `32`;
- step duration: `20..10000` ms.

Request body:

```json
{
  "name": "custom",
  "repeat": true,
  "steps": [
    { "color": "#ff0000", "ms": 100 },
    { "color": "#000000", "ms": 100 },
    { "color": "#ff0000", "ms": 100 },
    { "color": "#000000", "ms": 800 }
  ]
}
```

Step fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `color` | string, array, or object | no | Color as `#rrggbb`, `[r, g, b]`, or `{ "r": 255, "g": 0, "b": 0 }`. |
| `hex` | string | no | Alternative to `color`. |
| `on` | boolean | no | `true` uses base color, `false` turns the zone off. |
| `ms` | integer | no | Step duration in ms. Default `100`. |
| `duration` | integer | no | Alias for `ms`. |
| `fade` | boolean | no | Smoothly fade from current color to target color over the step duration. |

Example:

```sh
curl -X POST http://tardis-esp.local/api/zones/lamp/custom \
  -H "Content-Type: application/json" \
  -d '{
    "name": "soft-blue",
    "repeat": true,
    "steps": [
      { "color": "#001133", "ms": 400, "fade": true },
      { "color": "#00a3ff", "ms": 900, "fade": true },
      { "color": "#000000", "ms": 700, "fade": true }
    ]
  }'
```

## Error Responses

Errors return HTTP `400`, `404`, or `500` with JSON:

```json
{
  "error": "Unknown pattern"
}
```

Common errors:

| Error | Cause |
| --- | --- |
| `Unknown zone` | Zone slug is not configured. |
| `Zone is disabled` | The zone exists but `enabled=false`. |
| `Unknown pattern` | `name` is not one of the built-in pattern names. |
| `Missing pattern` | `GET /custom` was called without `pattern`. |
| `Missing JSON body` | `POST /custom` was called without a body. |
| `invalid JSON` | JSON body could not be parsed. |
| `steps must be a non-empty list` | JSON body has no valid `steps` array. |
| `too many steps` | Custom pattern has more than `32` steps. |
| `Request body is too large` | POST body is larger than `2048` bytes. |

## Persistence

Every enabled-zone control endpoint saves the selected behavior into `led_state.json`:

```json
{
  "zones": {
    "lamp": {
      "mode": "pattern",
      "pattern": "heartbeat",
      "color": [255, 0, 0],
      "interval_ms": 500,
      "repeat": true
    }
  }
}
```

Disabled zones are not saved.

On boot:

1. Saved zone state is loaded.
2. Startup animation runs without saving state:
   - `windows` fade into dim orange for about 5 seconds;
   - `signs` flicker like a failing lamp, then settle into white;
   - `lamp` emits two bright white flashes.
3. Wi-Fi connection starts. During Wi-Fi connection, `lamp` shows red double blinks.
4. After Wi-Fi connects, `lamp` is solid white for 5 seconds.
5. Saved state is restored for enabled zones.

The startup animation, Wi-Fi indicator, and white connected indicator are not saved as user state.
