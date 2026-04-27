import uasyncio as asyncio

from boot_animation import run_boot_animation
from led_control import load_led_state, restore_led_state
from web_server import start_http_server
from wifi_status import connect_wifi, show_connected_indicator


async def main():
    saved_state = load_led_state()
    await run_boot_animation()
    wlan = await connect_wifi()

    if not wlan.isconnected():
        while True:
            await asyncio.sleep(3600)

    await show_connected_indicator()
    restore_led_state(saved_state)
    await start_http_server(wlan)


asyncio.run(main())
