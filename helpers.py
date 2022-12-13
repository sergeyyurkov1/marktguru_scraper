from os import path
import dash_bootstrap_components as dbc


def check_chrome_exe_path(p: str) -> bool:
    return "chrome.exe" in p and path.exists(p)


def check_chrome_driver_exe_path() -> bool:
    return path.exists("chromedriver.exe")


def load_txt_file(file) -> str:
    try:
        with open(f"{file}.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        with open(f"{file}.txt", "w") as f:
            f.write("")

            return ""


def write_txt_file(file: str, txt: str) -> None:
    try:
        with open(f"{file}.txt", "w") as f:
            f.write(txt)
    except Exception as e:
        print(e)


def read_list(input: str) -> list:
    return [
        line.rstrip().lower()
        for line in input.splitlines()
        if not line.startswith("#") and not line.rstrip() == ""
    ]  # strips spaces and new lines


def get_alert(c, color):
    return (
        dbc.Alert(
            c,
            color=color,
            id="alert",
            is_open=True,
            duration=2500,
        ),
    )
