import network
import uasyncio as asyncio

from config import DEVICE_HOSTNAME, WIFI_PASSWORD, WIFI_SSID
from led_control import get_zone


def lamp_zone():
    return get_zone("lamp")


async def wifi_connect_indicator():
    led = lamp_zone()
    if led is None:
        return

    led._cancel_animation()

    try:
        while True:
            for _ in range(2):
                led._write((255, 0, 0))
                await asyncio.sleep_ms(120)
                led._write((0, 0, 0))
                await asyncio.sleep_ms(160)
            await asyncio.sleep_ms(650)
    except asyncio.CancelledError:
        raise


async def show_connected_indicator():
    led = lamp_zone()
    if led is None:
        return

    led._cancel_animation()
    led._write((255, 255, 255))
    await asyncio.sleep(5)


async def connect_wifi():
    try:
        network.hostname(DEVICE_HOSTNAME)
    except (AttributeError, ValueError) as exc:
        print("Hostname setup skipped:", exc)

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    indicator_task = None

    if not wlan.isconnected():
        print("Connecting to Wi-Fi:", WIFI_SSID)
        indicator_task = asyncio.create_task(wifi_connect_indicator())
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        for _ in range(80):
            if wlan.isconnected():
                break
            await asyncio.sleep_ms(250)

    if indicator_task:
        indicator_task.cancel()
        await asyncio.sleep_ms(0)

    if wlan.isconnected():
        print("Wi-Fi connected:", wlan.ifconfig())
        print("Hostname:", network.hostname())
    else:
        led = lamp_zone()
        if led:
            led.pattern_flash((255, 0, 0))
        print("Wi-Fi connection failed")

    return wlan
