import uasyncio as asyncio

from led_control import get_zone


WINDOWS_DIM_ORANGE = (80, 28, 0)
SIGN_DIM_WHITE = (70, 70, 60)
SIGN_HALF_WHITE = (150, 150, 130)
SIGN_FULL_WHITE = (255, 255, 235)
LAMP_FULL_WHITE = (255, 255, 255)
OFF = (0, 0, 0)


async def fade_zone(zone_name, color, duration_ms, steps=50):
    zone = get_zone(zone_name)
    if zone is None:
        return

    zone._cancel_animation()
    pause_ms = max(1, duration_ms // steps)

    for step in range(steps + 1):
        zone._write((
            color[0] * step // steps,
            color[1] * step // steps,
            color[2] * step // steps,
        ))
        await asyncio.sleep_ms(pause_ms)


async def signs_flicker():
    signs = get_zone("signs")
    if signs is None:
        return

    signs._cancel_animation()

    sequence = (
        (SIGN_FULL_WHITE, 70),
        (OFF, 130),
        (SIGN_FULL_WHITE, 40),
        (OFF, 210),
        (SIGN_DIM_WHITE, 260),
        (OFF, 90),
        (SIGN_HALF_WHITE, 110),
        (OFF, 120),
        (SIGN_FULL_WHITE, 80),
        (OFF, 180),
        (SIGN_DIM_WHITE, 170),
        (OFF, 80),
        (SIGN_FULL_WHITE, 260),
    )

    for color, duration_ms in sequence:
        signs._write(color)
        await asyncio.sleep_ms(duration_ms)


async def lamp_flashes():
    lamp = get_zone("lamp")
    if lamp is None:
        return

    lamp._cancel_animation()

    for duration_ms in (110, 160):
        lamp._write(LAMP_FULL_WHITE)
        await asyncio.sleep_ms(duration_ms)
        lamp._write(OFF)
        await asyncio.sleep_ms(170)


async def run_boot_animation():
    await fade_zone("windows", WINDOWS_DIM_ORANGE, 5000)
    await signs_flicker()
    await lamp_flashes()
