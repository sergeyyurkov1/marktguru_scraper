import os
import contextlib

from selenium.webdriver import Chrome
from selenium.webdriver import ChromeOptions


def get_driver(chrome_binary_location, headless=False):
    options = ChromeOptions()

    options.add_argument("--start-maximized")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")

    if headless == True:
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless=chrome")
        options.add_argument("--disable-gpu")

    wd = os.path.join(os.getcwd(), "Chrome")
    options.add_argument(rf"user-data-dir={wd}")
    options.add_argument("profile-directory=Profile")
    options.add_argument("--log-level=3")

    options.binary_location = chrome_binary_location

    driver = Chrome(
        options=options,
    )

    return driver


@contextlib.contextmanager
def Driver(chrome_binary_location, headless):
    d = get_driver(chrome_binary_location, headless)
    try:
        yield d
    finally:
        d.close()
