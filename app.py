import os

import dash
import logging
from dash import Dash, dcc, html, Input, Output, State, no_update
import dash_bootstrap_components as dbc

# removing mantine for now
# import dash_mantine_components as dmc

from settings import APP_URL
from auth_setup import server, auth

from layout.navbar import Navbar
from layout.footer import Footer

BOOTSTRAP_ICONS = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"

here = os.path.dirname(os.path.abspath(__file__))
assets_path = os.path.join(here, "assets")
server.static_folder = assets_path
server.static_url_path = "/assets"

app = Dash(
    __name__,
    server=server,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        BOOTSTRAP_ICONS,
        # dmc.styles.ALL,
    ],
    use_pages=True,
)

nav_links = [
    {'label':"Home",'url':"/home"},
    # {'label':"Entry",'url':"/entry"},
    # {'label':"Report",'url':"/report"}
]
navbar = Navbar(nav_links, id="navbar", title="Registration Dashboard", expand="lg")
navbar.register_callbacks(app)

footer = Footer()

app.layout = html.Div([

    dcc.Location(id="redirect-to", refresh=True),
    # expose current URL so we can avoid redirecting to the same href (prevents reload loops)
    dcc.Location(id="current-url"),
    dcc.Interval(
        id="init-interval",
        interval=500,  # e.g., 1 second after page load
        n_intervals=0,
        max_intervals=1  # This ensures it fires only once
    ),

    navbar.render(),

    dash.page_container,

    footer.render(),
])



@dash.callback(
    Output("redirect-to", "href"),
    Input("init-interval", "n_intervals"),
    State("current-url", "href"),
)
def initial_view(n, current_href):
    """On timeout, check token and redirect only when needed.

    Avoid redirecting to `APP_URL` when the app is already at that URL —
    that causes a reload loop on platforms (like Posit) where the app
    is served at `APP_URL`.
    """
    logger = logging.getLogger(__name__)
    logger.debug("initial_view: current_href=%s APP_URL=%s", current_href, APP_URL)

    try:
        token = auth.get_token()
    except Exception:
        # redirect to the app home page (avoid root 404s on Posit)
        desired = APP_URL.rstrip("/") + "/home"
        if current_href and current_href.startswith(desired):
            return no_update
        logger.info("No token; redirecting to %s", desired)
        return desired

    return no_update

if __name__ == "__main__":
    app.run(debug=True, port=8050)
