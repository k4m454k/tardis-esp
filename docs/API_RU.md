# API зон подсветки TARDIS ESP

ESP32-C3 запускает небольшой HTTP-сервер на порту `80`.

Базовый URL по умолчанию:

```text
http://tardis-esp.local
```

Если `.local` недоступен, используйте IP-адрес, напечатанный в serial-консоли:

```text
HTTP server listening on http://<ip>:80/
```

Эндпоинты управления светом работают только через зоны. Настроенные зоны: `lamp`, `windows` и `signs`.

## Зоны

| Зона | Значение | Включена | Пин | Пиксели |
| --- | --- | --- | --- | --- |
| `lamp` | Верхний фонарь | да | `GPIO10` | `1` |
| `windows` | Окна TARDIS | да | `GPIO8` | `3` |
| `signs` | Надписи `POLICE PUBLIC CALL BOX` | да | `GPIO7` | `3` |

Если зона отключена в `config.py`, для нее не создается объект `Pin`/`NeoPixel`. Управляющие эндпоинты отключенных зон возвращают:

```json
{
  "error": "Zone is disabled"
}
```

с HTTP `400`.

## Формат состояния

`GET /api/zones` возвращает все зоны и общее состояние железа:

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

`GET /api/zones/{zone}/state` возвращает объект одной зоны.

`GET /api/system` возвращает компактную диагностическую сводку с памятью heap и настройками обслуживания HTTP:

```json
{
  "memory": {
    "free": 65432,
    "allocated": 12345
  },
  "gc": {
    "file_chunk_bytes": 1024,
    "maintenance_seconds": 60
  }
}
```

Поля зоны:

| Поле | Тип | Описание |
| --- | --- | --- |
| `zone` | string | Идентификатор зоны: `lamp`, `windows` или `signs`. |
| `label` | string | Человекочитаемое название зоны. |
| `enabled` | boolean | Нужно ли прошивке создавать hardware-объекты и разрешать управление. |
| `ready` | boolean | Есть ли у зоны инициализированный объект `NeoPixel`. |
| `draft` | boolean | Является ли зона предварительно настроенной, но еще не финализированной. |
| `pin` | integer или null | GPIO-пин или `null` для отключенных draft-зон. |
| `pixel_count` | integer | Количество пикселей в цепочке зоны. |
| `mode` | string | `off`, `solid`, `blink`, `pulse`, `pattern`, `custom` или `disabled`. |
| `pattern` | string | Имя текущего паттерна. |
| `color` | object | Последний активный RGB-цвет. |
| `interval_ms` | integer | Текущее значение скорости или периода. |
| `repeat` | boolean | Повторяется ли активная последовательность. |
| `step_count` | integer | Количество шагов в кастомной последовательности. |
| `is_on` | boolean | Светится ли зона прямо в текущий момент. |

## Параметры цвета

Большинство управляющих эндпоинтов принимают либо:

```text
hex=ff0000
```

либо отдельные RGB-каналы:

```text
r=255&g=0&b=0
```

Правила:

- `hex` может включать `#` или быть без него, но в URL-примерах `#` опущен.
- `r`, `g` и `b` ограничиваются диапазоном `0..255`.
- Если цвет не передан, используется текущий сохраненный цвет зоны.

## Эндпоинты

### `GET /`

Возвращает веб-интерфейс из `index.html`.

### `GET /api/zones`

Возвращает все настроенные зоны.

Пример:

```sh
curl http://tardis-esp.local/api/zones
```

### `GET /api/system`

Запускает сборку мусора и возвращает диагностику heap. Полезно для проверки, не ломается ли веб-интерфейс из-за нехватки или фрагментации свободной памяти после долгой работы.

Пример:

```sh
curl http://tardis-esp.local/api/system
```

### `GET /api/zones/{zone}/state`

Возвращает состояние одной зоны.

Пример:

```sh
curl http://tardis-esp.local/api/zones/lamp/state
```

### `GET /api/zones/{zone}/off`

Выключает включенную зону и сохраняет состояние.

Пример:

```sh
curl http://tardis-esp.local/api/zones/lamp/off
```

### `GET /api/zones/{zone}/on`

Включает включенную зону сплошным цветом и сохраняет состояние.

Примеры:

```sh
curl "http://tardis-esp.local/api/zones/lamp/on?hex=ffffff"
curl "http://tardis-esp.local/api/zones/lamp/on?r=255&g=64&b=0"
```

### `GET /api/zones/{zone}/color`

Алиас для установки сплошного цвета. Сохраняет состояние.

Пример:

```sh
curl "http://tardis-esp.local/api/zones/lamp/color?hex=00a3ff"
```

### `GET /api/zones/{zone}/blink`

Запускает простой цикл включения и выключения, затем сохраняет состояние.

Query-параметры:

| Параметр | Обязательный | Описание |
| --- | --- | --- |
| `hex` или `r/g/b` | нет | Цвет моргания. |
| `interval` | нет | Длительность включенного и выключенного состояния в мс. По умолчанию `500`. |
| `interval_ms` | нет | Алиас для `interval`. |

Пример:

```sh
curl "http://tardis-esp.local/api/zones/lamp/blink?hex=ff0000&interval=300"
```

### `GET /api/zones/{zone}/pulse`

Запускает плавную пульсацию и сохраняет состояние.

Query-параметры:

| Параметр | Обязательный | Описание |
| --- | --- | --- |
| `hex` или `r/g/b` | нет | Цвет пульсации. |
| `period` | нет | Период пульсации в мс. По умолчанию `1500`. |
| `period_ms` | нет | Алиас для `period`. |

Пример:

```sh
curl "http://tardis-esp.local/api/zones/lamp/pulse?hex=00a3ff&period=1500"
```

### `GET /api/zones/{zone}/pattern`

Запускает именованный встроенный паттерн и сохраняет состояние.

Query-параметры:

| Параметр | Обязательный | Описание |
| --- | --- | --- |
| `name` | нет | Имя паттерна. По умолчанию `flash`. |
| `hex` или `r/g/b` | нет | Цвет паттерна. Игнорируется для `rainbow`. |
| `interval` | нет | Значение скорости, используемое `breathe` и `rainbow`. По умолчанию `500`. |
| `period` | нет | Алиас для `interval`. |

Поддерживаемые имена:

`flash`, `heartbeat`, `double`, `triple`, `sos`, `breathe`, `flicker`, `glitch`, `alarm`, `notify`, `rainbow`, `wifi`.

`glitch` оставляет зону светиться выбранным цветом и иногда добавляет короткие случайные мерцания, провалы яркости, полные отключения и короткие белые вспышки.

Примеры:

```sh
curl "http://tardis-esp.local/api/zones/lamp/pattern?name=heartbeat&hex=ff0000"
curl "http://tardis-esp.local/api/zones/lamp/pattern?name=rainbow&interval=700"
```

### `GET /api/zones/{zone}/custom`

Запускает кастомный паттерн из компактного query-string формата и сохраняет его.

Query-параметры:

| Параметр | Обязательный | Описание |
| --- | --- | --- |
| `pattern` | да | Компактная строка паттерна. |
| `hex` или `r/g/b` | нет | Базовый цвет. По умолчанию текущий цвет зоны. |
| `unit` | нет | Длительность в мс для символов бинарного паттерна. По умолчанию `150`. |
| `interval` | нет | Алиас для `unit`. |
| `repeat` | нет | `1`, `0`, `true`, `false`, `yes`, `no`, `on` или `off`. По умолчанию `true`. |
| `name` | нет | Имя кастомного паттерна, сохраняемое в state. По умолчанию `custom`. |

Бинарная форма:

```text
100101110
```

Каждая `1` означает базовый цвет на `unit` мс. Каждый `0` означает выключенное состояние на `unit` мс.

Форма с длительностями:

```text
1:120,0:120,1:120,0:800
```

Формат timed-токена:

```text
color_or_state:duration_ms[:fade]
```

Поддерживаемые значения `color_or_state`:

- `1` или `on`: базовый цвет.
- `0`, `off` или `black`: выключено.
- `ff0000` или `#ff0000`: явный цвет.

Примеры:

```sh
curl "http://tardis-esp.local/api/zones/lamp/custom?hex=ff0000&unit=150&pattern=100101110"
curl "http://tardis-esp.local/api/zones/lamp/custom?hex=00a3ff&pattern=1:120,0:120,1:120,0:800&name=double-custom"
curl "http://tardis-esp.local/api/zones/lamp/custom?pattern=ff0000:300:fade,000000:300:fade&repeat=true"
```

### `POST /api/zones/{zone}/custom`

Запускает кастомный паттерн из JSON и сохраняет его.

Ограничения:

- тело запроса: максимум `2048` байт;
- шагов: максимум `32`;
- длительность шага: `20..10000` мс.

Тело запроса:

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

Поля шага:

| Поле | Тип | Обязательное | Описание |
| --- | --- | --- | --- |
| `color` | string, array или object | нет | Цвет как `#rrggbb`, `[r, g, b]` или `{ "r": 255, "g": 0, "b": 0 }`. |
| `hex` | string | нет | Альтернатива `color`. |
| `on` | boolean | нет | `true` использует базовый цвет, `false` выключает зону. |
| `ms` | integer | нет | Длительность шага в мс. По умолчанию `100`. |
| `duration` | integer | нет | Алиас для `ms`. |
| `fade` | boolean | нет | Плавно перейти от текущего цвета к целевому за длительность шага. |

Пример:

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

## Ответы с ошибками

Ошибки возвращают HTTP `400`, `404` или `500` с JSON:

```json
{
  "error": "Unknown pattern"
}
```

Частые ошибки:

| Ошибка | Причина |
| --- | --- |
| `Unknown zone` | Идентификатор зоны не настроен. |
| `Zone is disabled` | Зона существует, но `enabled=false`. |
| `Unknown pattern` | `name` не входит в список встроенных паттернов. |
| `Missing pattern` | `GET /custom` вызван без `pattern`. |
| `Missing JSON body` | `POST /custom` вызван без тела запроса. |
| `invalid JSON` | JSON body не удалось распарсить. |
| `steps must be a non-empty list` | В JSON body нет валидного массива `steps`. |
| `too many steps` | В кастомном паттерне больше `32` шагов. |
| `Request body is too large` | POST body больше `2048` байт. |

## Сохранение состояния

Каждый управляющий endpoint включенной зоны сохраняет выбранное поведение в `led_state.json`:

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

Отключенные зоны не сохраняются.

При загрузке:

1. Загружается сохраненное состояние зон.
2. Запускается стартовая анимация без сохранения состояния:
   - `windows` плавно загораются неярким оранжевым примерно за 5 секунд;
   - `signs` мерцают как неисправная лампа, затем стабилизируются в белый;
   - `lamp` дает две яркие белые вспышки.
3. Начинается подключение к Wi-Fi. Во время подключения `lamp` показывает красные двойные мигания.
4. После подключения к Wi-Fi `lamp` светится сплошным белым 5 секунд.
5. Для включенных зон восстанавливается сохраненное состояние.

Стартовая анимация, индикатор подключения к Wi-Fi и белый индикатор успешного подключения не сохраняются как пользовательское состояние.
