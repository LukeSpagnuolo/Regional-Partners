import csv
import io
from datetime import datetime

from dash import html, dcc, Output, Input, State, no_update
from dash.exceptions import PreventUpdate
import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import dash_table

from settings import SITE_URL, REPORT_ROWS_ENDPOINT
from apps.reporting_client import ReportingAPIConfig, ReportingClient, ReportingClientError
from auth_setup import auth

from apps.utils import fetch_options, filters_to_params
from layout.offcanvas import OffcanvasComponent

dash.register_page(__name__, path="/home")

cfg = ReportingAPIConfig(
    base_url=SITE_URL,
    rows_path=REPORT_ROWS_ENDPOINT,
)
reporting = ReportingClient(cfg, token_getter=auth.get_token)

DEFAULT_COLUMNS = ["first_name", "last_name", "sport", "email"]
DEFAULT_PAGE_SIZE = 25

SEEDED_OPTIONS = [{"label": k, "value": k} for k in DEFAULT_COLUMNS]

STATUS_OPTIONS = [
    {"label": "Active", "value": "ACTIVE"},
    {"label": "Incomplete", "value": "INCOMPLETE"},
    {"label": "Pending", "value": "PENDING"},
    {"label": "Expired", "value": "EXPIRED"},
    {"label": "Superceded", "value": "SUPERSEDED"},
]

HIDDEN_ENROLLMENT_STATUS = ["ACTIVE", "EXPIRED"]
HIDDEN_ENROLLMENT_STATUS_SET = {status.upper() for status in HIDDEN_ENROLLMENT_STATUS}
HIDDEN_SPORTS = {"cinderball", "skimboard cross", "nordic vaulting"}

def _columns_to_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [c.strip() for c in value.split(",") if c.strip()]
    return []


def _columns_to_param(value) -> str:
    return ",".join(_columns_to_list(value))


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


# def _build_dt_columns(keys: list[str]) -> list[dict]:
#     return [{"name": k, "id": k} for k in keys]

def _build_dt_columns(keys: list[str], meta_payload: dict | None = None) -> list[dict]:
    label_map = {}

    if isinstance(meta_payload, dict):
        for col in meta_payload.get("columns", []):
            key = col.get("key")
            label = col.get("label")
            if key:
                label_map[str(key)] = str(label or key)

    return [{"id": key, "name": label_map.get(key, key)} for key in keys]

def _to_cell_value(v):
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, (list, tuple)):
        parts = []
        for item in v:
            if isinstance(item, dict):
                parts.append(
                    str(
                        item.get("label")
                        or item.get("name")
                        or item.get("value")
                        or item.get("id")
                        or ""
                    )
                )
            else:
                parts.append(str(item))
        parts = [p for p in parts if p]
        return ", ".join(parts)
    if isinstance(v, dict):
        return str(v.get("label") or v.get("name") or v.get("value") or v.get("id") or v)
    return str(v)


def _normalize_rows(rows: list, columns_value) -> list[dict]:
    keys = _columns_to_list(columns_value)

    out: list[dict] = []
    for r in rows or []:
        if isinstance(r, dict) and isinstance(r.get("cells"), dict):
            row = r["cells"]
        elif isinstance(r, dict):
            row = r
        elif isinstance(r, (list, tuple)) and keys:
            row = dict(zip(keys, r))
        else:
            continue

        out.append({k: _to_cell_value(row.get(k)) for k in keys})

    return out


def _row_enrollment_status(row) -> str:
    if isinstance(row, dict):
        if isinstance(row.get("cells"), dict):
            row = row["cells"]
        value = row.get("enrollment_status")
        if value is None:
            value = row.get("Enrollment Status")
        if value is None:
            return ""
        return str(value).strip().upper()
    return ""


def _row_sport_name(row) -> str:
    if isinstance(row, dict):
        if isinstance(row.get("cells"), dict):
            row = row["cells"]
        value = row.get("sport")
        if value is None:
            value = row.get("Sport")
        if value is None:
            value = row.get("sport_name")
        if value is None:
            value = row.get("sportName")
        if value is None:
            return ""
        sport_name = str(_to_cell_value(value)).strip().lower()
        sport_name = sport_name.replace("(test)", "")
        return " ".join(sport_name.split())
    return ""


def _filter_allowed_enrollment_rows(rows: list) -> list:
    return [
        row
        for row in rows or []
        if _row_enrollment_status(row) in HIDDEN_ENROLLMENT_STATUS_SET
        and _row_sport_name(row) not in HIDDEN_SPORTS
    ]

def filter_section(title: str, first: bool = False):
    return html.Div(
        title,
        className=f"{'' if first else 'mt-4'} mb-2 text-uppercase text-muted fw-semibold small border-bottom pb-1"
    )

filters_layout = dmc.MantineProvider(
    [
        filter_section("Nearest Campus", first=True),

        dbc.Label("Birthplace", className="mt-3"),
        dmc.MultiSelect(
            id="filter-birth-campus",
            data=[],
            value=[],
            placeholder="Select Campuses...",
            clearable=True,
            searchable=True,
            comboboxProps={"withinPortal": False, "zIndex": 2000},
        ),

        dbc.Label("Current Residence", className="mt-3"),
        dmc.MultiSelect(
            id="filter-current-campus",
            data=[],
            value=[],
            placeholder="Select Campuses...",
            clearable=True,
            searchable=True,
            comboboxProps={"withinPortal": False, "zIndex": 2000},
        ),

        filter_section("Sport Info"),

        dbc.Label("Sport", className="mt-3"),
        dcc.Dropdown(id="filter-sport", options=[], value=None, clearable=True),

        dbc.Label("Sport Level", className="mt-3"),
        dcc.Dropdown(id="filter-sportlevel", options=[], value=None, clearable=True),

        dbc.Label("Athlete Card", className="mt-3"),
        dmc.MultiSelect(
            id="filter-card",
            data=[],
            value=[],
            placeholder="Select carding levels...",
            clearable=True,
            searchable=True,
            comboboxProps={"withinPortal": False, "zIndex": 2000},
        ),

        filter_section("Registration"),

        dbc.Label("Role", className="mt-3"),
        dcc.Dropdown(id="filter-role", options=[], value=None, clearable=True),

        dbc.Button("Apply Filters", id="apply-filters", color="primary", className="mt-3"),
    ]
)

fields_layout = [
    dbc.Label("Fields", className="mt-3"),
    dcc.Checklist(
        id="columns-select",
        options=SEEDED_OPTIONS,
        value=DEFAULT_COLUMNS,
        inputStyle={"marginRight": "0.5rem"},
        labelStyle={"display": "block", "marginBottom": "0.35rem"},
        style={
            "maxHeight": "60vh",
            "overflowY": "auto",
        },
        persistence=True,
        persistence_type="local",
    ),
    dbc.Button("Apply Fields", id="apply-columns", color="primary", className="mt-3"),
]

filters_panel = OffcanvasComponent(
    id_prefix="reg-search-filters",
    title="Filters",
    children=filters_layout,
    placement="end",
    toggle_classname='me-2',
    toggle_children=html.I(className="bi bi-filter"),
)

fields_panel = OffcanvasComponent(
    id_prefix="reg-search-fields",
    title="Fields",
    children=fields_layout,
    placement="end",
    toggle_classname='me-2',
    toggle_children=html.I(className="bi bi-table"),
)

layout = dbc.Container(
    [
        dcc.Interval(id="init-load", interval=500, n_intervals=0),

        dcc.Store(id="columns-meta-store"),
        dcc.Store(id="applied-filters-store", data={}),
        dcc.Store(id="applied-columns-store", data=DEFAULT_COLUMNS),
        dcc.Download(id="download-csv"),

        html.Div(
            [
                dbc.Toast(
                    id="columns-toast",
                    header="Columns",
                    is_open=False,
                    dismissable=True,
                    duration=2000,
                    icon="info",
                ),
                dbc.Toast(
                    id="rows-toast",
                    header="Rows",
                    is_open=False,
                    dismissable=True,
                    duration=2000,
                    icon="info",
                ),
            ],
            style={
                "position": "fixed",
                "top": "1rem",
                "left": "50%",
                "transform": "translateX(-50%)",
                "width": "420px",
                "maxWidth": "90vw",
                "zIndex": 2000,
            },
        ),

        dbc.Row(
            [
                dbc.Col([html.H3("Registration Data")]),
                dbc.Col(
                    [
                        dbc.Button(
                            html.I(className="bi bi-download"),
                            id="download-csv-btn",
                            color="secondary",
                            className="me-2",
                        ),
                        fields_panel.toggle_button,
                        filters_panel.toggle_button,
                    ],
                    width="auto",
                    className="ms-auto d-flex justify-content-end",
                ),
            ],
            className="my-3 align-items-start",
        ),

        filters_panel.offcanvas,
        fields_panel.offcanvas,

        dash_table.DataTable(
            id="rows-table",
            columns=_build_dt_columns(DEFAULT_COLUMNS),
            data=[],
            page_action="custom",
            page_current=0,
            page_size=DEFAULT_PAGE_SIZE,
            sort_action="none",
            filter_action="none",
            # style_table={"height": "70vh", "overflowY": "auto"},
            # style_cell={
            #     "padding": "0.35rem",
            #     "whiteSpace": "normal",
            #     "height": "auto",
            #     "textAlign": "left",
            # },
            # style_header={"fontWeight": "600"},
            style_table={
                "overflowX": "auto",
            },
            style_cell={
                "fontFamily": "Arial, sans-serif",
                "fontSize": "0.875rem",
                "padding": "0.25rem 0.5rem",
                "textAlign": "left",
                "whiteSpace": "normal",
                "height": "auto",
            },
            style_header={
                "fontFamily": "Arial, sans-serif",
                "fontSize": "0.875rem",
                "fontWeight": "600",
                "textAlign": "left",
            },
        ),
    ],
    fluid=True,
)


@dash.callback(
    Output("init-load", "disabled"),
    Output("filter-role", "options"),
    Output("filter-birth-campus", "data"),
    Output("filter-current-campus", "data"),
    Output("filter-sport", "options"),
    Output("filter-card", "data"),
    Output("filter-sportlevel", "options"),
    Input("init-load", "n_intervals"),
    prevent_initial_call=False,
)
def load_filters(_n):
    try:
        _ = auth.get_token()
    except Exception:
        raise PreventUpdate

    campus_options = fetch_options("/api/registration/campus/", auth.get_token(), "name", "id")
    role_options = fetch_options("/api/registration/role/", auth.get_token(), "verbose_name", "id")
    sport_options = fetch_options("/api/registration/sport/", auth.get_token(), "name", "id")
    card_options = fetch_options("/api/registration/card/", auth.get_token(), "name", "id")
    level_options = fetch_options("/api/registration/sportlevel/", auth.get_token(), "name", "id")

    return True, role_options, campus_options, campus_options, sport_options, card_options, level_options


@dash.callback(
    Output("applied-filters-store", "data"),
    Output("reg-search-filters-offcanvas", "is_open", allow_duplicate=True),
    Output("rows-table", "page_current", allow_duplicate=True),
    Input("apply-filters", "n_clicks"),
    State("filter-sport", "value"),
    State("filter-sportlevel", "value"),
    State("filter-role", "value"),
    State("filter-card", "value"),
    State("filter-birth-campus", "value"),
    State("filter-current-campus", "value"),
    prevent_initial_call=True,
)
def apply_filters(
    _n,
    sport_id,
    sport_level,
    role_id,
    card_ids,
    birth_campus_ids,
    current_campus_ids,
):

    raw = {
        "sport_id": sport_id,
        "sport_level_id": sport_level,
        "role_id": role_id,
        "athlete_carding_ids": card_ids,
        "birth_city_campus_id": birth_campus_ids,
        "residence_city_campus_id": current_campus_ids,
    }
    applied = filters_to_params(raw)
    return applied, False, 0


@dash.callback(
    Output("columns-select", "options"),
    Output("columns-select", "value"),
    Output("applied-columns-store", "data"),
    Output("columns-meta-store", "data"),
    Output("columns-toast", "children"),
    Output("columns-toast", "icon"),
    Output("columns-toast", "is_open"),
    Input("init-load", "n_intervals"),
    State("columns-select", "value"),
    prevent_initial_call=False,
)
def load_columns_options(_n_intervals, current_value):
    current = _columns_to_list(current_value) or list(DEFAULT_COLUMNS)

    try:
        _ = auth.get_token()
    except Exception:
        return (
            SEEDED_OPTIONS,
            current,
            current,
            None,
            "No access token yet (columns fetch skipped).",
            "warning",
            True,
        )

    try:
        payload = reporting.list_columns()
        cols = payload.get("columns") or []

        options: list[dict] = []
        for c in cols:
            if not isinstance(c, dict):
                continue
            key = c.get("key")
            if not key:
                continue
            label = c.get("label") or key
            if "nomination" in str(key).lower() or "nomination" in str(label).lower():
                continue
            options.append({"label": str(label), "value": str(key)})

        options.sort(key=lambda o: o["label"].lower())

        valid = {o["value"] for o in options}
        current = [v for v in current if v in valid]

        if not current:
            fallback = [v for v in DEFAULT_COLUMNS if v in valid]
            current = fallback or ([options[0]["value"]] if options else [])

        return options, current, current, payload, "Loaded columns metadata.", "success", True

    except ReportingClientError as e:
        message = str(e)
        if "403 Forbidden" in message or "403" in message:
            return (
                SEEDED_OPTIONS,
                current,
                current,
                None,
                "Column metadata is not available for this account; using default columns.",
                "warning",
                True,
            )
        return (
            SEEDED_OPTIONS,
            current,
            current,
            None,
            f"ReportingClientError (columns): {e}",
            "danger",
            True,
        )
    except Exception as e:
        return (
            SEEDED_OPTIONS,
            current,
            current,
            None,
            f"Unexpected error (columns): {e}",
            "danger",
            True,
        )


@dash.callback(
    Output("applied-columns-store", "data", allow_duplicate=True),
    Output("reg-search-fields-offcanvas", "is_open", allow_duplicate=True),
    Output("rows-table", "page_current", allow_duplicate=True),
    Input("apply-columns", "n_clicks"),
    State("columns-select", "value"),
    prevent_initial_call=True,
)
def apply_columns(_n, columns_value):
    applied = _columns_to_list(columns_value) or list(DEFAULT_COLUMNS)
    return applied, False, 0


@dash.callback(
    Output("rows-table", "columns"),
    Input("applied-columns-store", "data"),
    State("columns-meta-store", "data"),
)
def configure_table(columns_value, meta_payload):
    keys = _columns_to_list(columns_value) or list(DEFAULT_COLUMNS)
    return _build_dt_columns(keys, meta_payload)


@dash.callback(
    Output("rows-table", "data"),
    Output("rows-toast", "children"),
    Output("rows-toast", "icon"),
    Output("rows-toast", "is_open"),
    Input("rows-table", "page_current"),
    Input("rows-table", "page_size"),
    Input("applied-columns-store", "data"),
    Input("applied-filters-store", "data"),
    prevent_initial_call=False,
)
def fetch_rows(page_current, page_size, columns_value, applied_filters):
    try:
        _ = auth.get_token()
    except Exception:
        return [], "No access token yet (table fetch skipped).", "warning", True

    page_current = int(page_current or 0)
    page_size = int(page_size or DEFAULT_PAGE_SIZE)

    limit = max(page_size, 1)
    offset = max(page_current * page_size, 0)

    params = {"limit": limit, "offset": offset}
    requested_columns = _columns_to_list(columns_value) or list(DEFAULT_COLUMNS)
    fetch_columns = _dedupe_preserve_order(requested_columns + ["enrollment_status", "sport"])
    cols = _columns_to_param(fetch_columns)
    if cols:
        params["columns"] = cols
    if isinstance(applied_filters, dict) and applied_filters:
        params.update(applied_filters)

    try:
        payload = reporting._GET_json(reporting.config.rows_url, params=params)

        if isinstance(payload, dict) and "results" in payload:
            rows = payload.get("results") or []
            total = payload.get("count", None)
            _ = total
        elif isinstance(payload, list):
            rows = payload
        else:
            rows = []

        rows = _filter_allowed_enrollment_rows(rows)
        data = _normalize_rows(rows, requested_columns)
        return data, no_update, no_update, no_update

    except ReportingClientError as e:
        return [], f"ReportingClientError: {e}", "danger", True
    except Exception as e:
        return [], f"Unexpected error: {e}", "danger", True


@dash.callback(
    Output("download-csv", "data"),
    Input("download-csv-btn", "n_clicks"),
    State("applied-columns-store", "data"),
    State("applied-filters-store", "data"),
    prevent_initial_call=True,
)
def download_full_dataset(n_clicks, columns_value, applied_filters):
    if not n_clicks:
        return no_update

    try:
        _ = auth.get_token()
    except Exception:
        raise PreventUpdate

    keys = _columns_to_list(columns_value) or list(DEFAULT_COLUMNS)
    cols = _columns_to_param(_dedupe_preserve_order(keys + ["enrollment_status", "sport"]))

    limit = 1000
    offset = 0

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
    writer.writeheader()

    while True:
        params = {"limit": limit, "offset": offset}
        if cols:
            params["columns"] = cols
        if isinstance(applied_filters, dict) and applied_filters:
            params.update(applied_filters)

        payload = reporting._GET_json(reporting.config.rows_url, params=params)

        if isinstance(payload, dict):
            rows = payload.get("results") or []
            total = payload.get("count")
            next_url = payload.get("next")
        elif isinstance(payload, list):
            rows = payload
            total = None
            next_url = None
        else:
            rows = []
            total = None
            next_url = None

        rows = _filter_allowed_enrollment_rows(rows)

        if not rows:
            break

        normalized = _normalize_rows(rows, keys)
        for row in normalized:
            writer.writerow(row)

        if next_url:
            offset += len(rows)
            continue

        if total is not None and (offset + len(rows)) >= int(total):
            break

        offset += len(rows)

    filename = f"report_rows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return dict(content=buf.getvalue(), filename=filename, type="text/csv")