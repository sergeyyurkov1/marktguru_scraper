import os, shutil
from psutil import NoSuchProcess
from threading import Timer
import webbrowser
import logging

from dash import (
    Dash,
    dcc,
    html,
    Input,
    Output,
    State,
    no_update
)
from dash.long_callback import DiskcacheLongCallbackManager
import diskcache
import dash_bootstrap_components as dbc

from helpers import (
    check_chrome_exe_path,
    load_txt_file,
    write_txt_file,
    read_list,
    get_alert,
    check_chrome_driver_exe_path,
)

from selenium_init import Driver
from marktguru_scraper import set_location, launch_scraper, generate_output


# ---------------------------
try:
    shutil.rmtree("cache")
    shutil.rmtree("Chrome")
except (PermissionError, FileNotFoundError):
    pass


cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)


# ---------------------------
def launch_app_mode() -> None:
    webbrowser.open_new("http://127.0.0.1:8050")


def App() -> None:
    external_stylesheets = [dbc.themes.UNITED]

    app = Dash(
        __name__,
        external_stylesheets=external_stylesheets,
        suppress_callback_exceptions=True,
        long_callback_manager=long_callback_manager,
    )

    SIDEBAR_STYLE = {
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "20rem",
        "padding": "2rem 1rem",
        "background-color": "#f8f9fa",
    }

    CONTENT_STYLE = {
        "margin-left": "22rem",
        "margin-right": "2rem",
        "padding": "2rem 1rem",
    }

    sidebar = html.Div(
        [
            dcc.Store(id="store", storage_type="local"),
            html.H2("MarktGuru Scraper", className="display-6"),
            html.Hr(),
            html.Div(
                [
                    dbc.Label("Search URL"),
                    dbc.Input(
                        value="https://www.marktguru.de/search",
                        size="md",
                        className="mb-3",
                        id="url-input",
                        readonly=True,
                    ),
                ]
            ),
            html.Div(
                [
                    dbc.Label("Path to Chrome executable"),
                    dbc.InputGroup(
                        [
                            dbc.Input(
                                value="C:\Program Files\Google\Chrome\Application\chrome.exe",
                                size="md",
                                id="path-input",
                            ),
                            dbc.Button(
                                "Check",
                                color="primary",
                                n_clicks=0,
                                className="me-1",
                                id="check-button",
                            ),
                        ]
                    ),
                ]
            ),
            html.Hr(),
            html.Div(
                [
                    dbc.Label("ZIP code"),
                    dbc.Input(
                        value="10713", size="md", className="mb-3", id="zip-input"
                    ),
                ]
            ),
            html.Div(
                [
                    dbc.Label("Display lowest price by"),
                    dbc.RadioItems(
                        options=[
                            {"label": "Search item", "value": "Item"},
                            {"label": "Product name", "value": "Name"},
                        ],
                        value="Item",
                        id="lp-input",
                        className="mb-3",
                        inline=True,
                    ),
                ]
            ),
            html.Div(
                [
                    dbc.Label("Margin of error"),
                    dbc.Input(
                        type="number", value=0, min=0, max=10, step=1, id="moe-input"
                    ),
                    dbc.Tooltip(
                        "The maximum number of empty results to skip in case of errors on a product page",
                        target="moe-input",
                        placement="right",
                    ),
                ],
                id="styled-numeric-input",
                className="mb-4",
            ),
            html.Div(
                [
                    dbc.Button(
                        "Save",
                        color="primary",
                        n_clicks=0,
                        className="me-1",
                        outline=True,
                        id="save-button",
                        disabled=False,
                    ),
                ],
                className="d-grid gap-2 col-6 mx-auto",
            ),
        ],
        style=SIDEBAR_STYLE,
    )

    content = html.Div(id="page-content", style=CONTENT_STYLE)

    app.layout = html.Div([dcc.Location(id="url"), sidebar, content])

    main = html.Div(
        [
            html.Div(
                [
                    dbc.Row(
                        id="top-row-0",
                    ),
                    dbc.Row(
                        id="top-row-1",
                    ),
                    dbc.Row(id="top-row-2"),
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Div(
                                    [
                                        dbc.Label("Shopping list"),
                                        dbc.Textarea(
                                            style={"height": "16rem"},
                                            draggable=False,
                                            placeholder="Comment out the items you don't want to buy today - prepend the '#' symbol to the name",
                                            id="shopping-list",
                                        ),
                                    ]
                                )
                            ),
                            dbc.Col(
                                html.Div(
                                    [
                                        dbc.Label("Blacklist"),
                                        dbc.Textarea(
                                            style={"height": "16rem"},
                                            draggable=False,
                                            placeholder="Put items you don't want to see in search results here. Temporarily unlist an item by prepending '#' to the name",
                                            id="item-blacklist",
                                        ),
                                    ]
                                )
                            ),
                        ],
                        class_name="mb-4",
                    ),
                    html.Div(
                        [
                            dbc.Button(
                                "Scrape",
                                color="primary",
                                n_clicks=0,
                                className="me-1",
                                id="scrape-button",
                            ),
                            dbc.Button(
                                "Stop",
                                color="primary",
                                outline=True,
                                n_clicks=0,
                                className="me-1",
                                id="stop-button",
                                style={"visibility": "hidden"},
                            ),
                            dcc.Input(id="hidden-in", style={"visibility": "hidden"}),
                            html.Div(id="hidden-out", style={"visibility": "hidden"}),
                            dbc.Button(
                                "Open results",
                                color="success",
                                n_clicks=0,
                                className="me-1",
                                id="results-button",
                                style={"visibility": "hidden"},
                            ),
                        ],
                        className="d-grid gap-2 col-5 mx-auto",
                    ),
                ]
            ),
            html.Div(
                [
                    html.Hr(),
                    dbc.Label("Starting", id="label-1"),
                    html.Span(id="span"),
                    dbc.Label(id="label-2"),
                    dbc.Progress(
                        value=100,
                        id="progress",
                        animated=True,
                        striped=True,
                    ),
                ],
                id="progress-container",
                style={"visibility": "hidden"},
            ),
        ],
        id="container",
    )

    # ---------------------------------------------------------------------------------
    @app.callback(
        Output("path-input", "value"),
        Output("zip-input", "value"),
        Output("lp-input", "value"),
        Output("moe-input", "value"),
        Input("store", "modified_timestamp"),
        State("store", "data"),
    )
    def get_from_store(modified_timestamp, data):
        d = {
            "path": "C:\Program Files\Google\Chrome\Application\chrome.exe",
            "zip": "10713",
            "lp": "Item",
            "moe": 0,
        }

        data = data or d

        return (
            data.get("path"),
            data.get("zip"),
            data.get("lp"),
            data.get("moe"),
        )

    @app.callback(
        Output("top-row-0", "children"),
        Output("store", "data"),
        State("path-input", "value"),
        State("zip-input", "value"),
        State("lp-input", "value"),
        State("moe-input", "value"),
        State("store", "data"),
        Input("save-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def set_to_store(path_, zip_, lp, moe, store_data, n_clicks):
        if n_clicks:
            store_data = store_data or {}

            store_data["path"] = path_
            store_data["zip"] = zip_
            store_data["lp"] = lp
            store_data["moe"] = int(moe)

            return get_alert("Settings saved", "success"), store_data

    @app.callback(
        Output("hidden-out", "children"),
        Input("results-button", "n_clicks"),
        State("hidden-in", "value"),
        prevent_initial_call=True,
    )
    def open_file(n_clicks, value):
        os.startfile(value)

        return ""

    @app.callback(
        Output("shopping-list", "value"),
        Output("item-blacklist", "value"),
        Input("check-button", "n_clicks"),
    )
    def load_lists(n_clicks):
        return load_txt_file("shopping_list"), load_txt_file("item_blacklist")

    @app.callback(
        Output("top-row-2", "children"),
        Input("check-button", "n_clicks"),
        State("path-input", "value"),
    )
    def toggle_path_alert(n_clicks, value):
        if n_clicks:
            exists = check_chrome_exe_path(value)
            if exists:
                return get_alert("Chrome executable found", "success")
            return get_alert("Chrome executable not found", "danger")

    # ---------------------------------------------------------------------------------
    @app.long_callback(
        prevent_initial_call=True,
        output=[
            Output("top-row-1", "children"),
            Output("results-button", "style"),
            Output("hidden-in", "value"),
        ],
        inputs=[
            Input("scrape-button", "n_clicks"),
            State("url-input", "value"),
            State("path-input", "value"),
            State("zip-input", "value"),
            State("lp-input", "value"),
            State("moe-input", "value"),
            State("shopping-list", "value"),
            State("item-blacklist", "value"),
        ],
        running=[
            (Output("scrape-button", "disabled"), True, False),
            (
                Output("stop-button", "style"),
                {"visibility": "visible"},
                {"visibility": "hidden"},
            ),
            (
                Output("progress-container", "style"),
                {"visibility": "visible"},
                {"visibility": "hidden"},
            ),
        ],
        progress=[
            Output("label-1", "children"),
            Output("span", "children"),
            Output("label-2", "children"),
            Output("progress", "value"),
        ],
        cancel=[Input("stop-button", "n_clicks")],
    )
    def scrape(
        set_progress,
        n_clicks,
        url,
        path_,
        zip_,
        lp,
        moe,
        shopping_list,
        item_blacklist,
    ):
        try:
            if (
                n_clicks
                and check_chrome_exe_path(path_)
                and check_chrome_driver_exe_path()
            ):
                write_txt_file("shopping_list", shopping_list)
                write_txt_file("item_blacklist", item_blacklist)

                sl = read_list(shopping_list)
                ib = read_list(item_blacklist)

                if len(sl) == 0:
                    return get_alert("Shopping list is empty", "danger"), no_update, no_update

                with Driver(path_, headless=True) as driver:
                    set_progress(("Setting location", "", "", 10))
                    set_location(driver, sl[0], zip_)
                    set_progress(("Location set", "", "", 25))

                    set_progress(("Scraping", "", "", 60))
                    # data = []
                    # try:
                    #     t = Thread(
                    #         target=launch_scraper, args=(path_, url, moe, sl, data, zip_)
                    #     )
                    #     t.start()
                    #     t.join()
                    # except (KeyboardInterrupt):
                    #     t.join()
                    #     t.terminate()

                    #     sys.exit()
                    data = launch_scraper(driver, url, moe, sl, zip_)
                set_progress(("Done scraping", "", "", 80))

                set_progress(("Processing data", "", "", 90))
                file = generate_output(data, lp, ib)
                set_progress(("Done", "", "", 100))

                return get_alert("Done", "success"), {"visibility": "visible"}, file

        except ProcessLookupError:
            print("ProcessLookupError")
        except NoSuchProcess:
            print("NoSuchProcess")

    @app.callback(Output("page-content", "children"), [Input("url", "pathname")])
    def render_page_content(pathname):
        if pathname == "/":
            return main

        return html.Div(
            [html.A("Go Home", href="/")],
            className="p-3",
        )

    Timer(1, launch_app_mode).start()

    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    app.run_server(debug=False)  # debug=True, use_reloader=False


if __name__ == "__main__":
    App()
