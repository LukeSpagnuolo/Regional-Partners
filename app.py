import os

import dash
from dash import Dash, dcc, html, Input, Output, no_update
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
    Input("init-interval", "n_intervals")
)
def initial_view(n):
    """
    On timeout, load filters
    """
    try:
        token = auth.get_token()
    except Exception as e:
        return APP_URL

    return no_update

if __name__ == "__main__":
    app.run(debug=True, port=8050)
