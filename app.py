import os
from datetime import datetime

import dash
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from dash import Input, Output, callback, dash_table, dcc, html
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('HOST')}:{os.getenv('PORT')}/{os.getenv('DATABASE')}"

USERS_SYNC_URL = "https://pxvwsqknvdmvskvbuunm.supabase.co/functions/v1/get-users-sasi-pro"

SECRETARIAS_MAP = {
    5855: "Prefeitura",
    17514: "Prefeitura",
    5852: "Prefeitura",
    5995: "Saúde",
    10860: "Saúde",
    6862: "Assistência Social",
    10866: "Obras / Serviços",
    12676: "Premiação",
    19856: "Dose de Cuidados",
    19851: "Dose de Cuidados",
    17770: "Dose de Cuidados",
}

STATUS_TRIAGEM = ["Assigned", "Triagem"]

STATUS_MAP = {
    "Assigned": "Atribuído",
    "Triagem": "Triagem",
    "Participante": "Participante",
    "Duplicado": "Duplicado",
    "Prefeitura": "Prefeitura",
    "Closed": "Concluído",
    "Reprovado": "Reprovado",
    "Secretaria de Serviço Social": "Assistência Social",
    "Secretaria de Obra": "Obras",
}

STATUS_CONCLUIDO = "Concluído"

COLORS = {
    "primary": "#1a365d",
    "secondary": "#2b6cb0",
    "accent": "#38a169",
    "warning": "#dd6b20",
    "danger": "#e53e3e",
    "bg": "#f7fafc",
    "card": "#ffffff",
    "text": "#2d3748",
    "text_light": "#718096",
}

CHART_COLOR_PALETTE = [
    "#14622C",
    "#F2A426",
    "#38a169",
    "#dd6b20",
    "#e53e3e",
    "#2b6cb0",
    "#1a365d",
    "#718096",
]

app = dash.Dash(
    __name__,
    external_stylesheets=["/assets/custom.css"],
    suppress_callback_exceptions=True,
)


def get_data():
    engine = create_engine(DB_URL)
    query = """
        SELECT
            e.id,
            e.alert_id,
            e.channel_id,
            ch.name AS channel_name,
            e.created_at,
            cs.name AS current_status,
            cs.color AS status_color,
            e.data,
            (SELECT sh.created_at FROM status_history sh
             WHERE sh.sasi_event_id = e.alert_id AND sh.type = 'STATUS' AND sh.text = 'Concluído'
             ORDER BY sh.created_at ASC LIMIT 1) AS closed_at
        FROM sasi_events e
        LEFT JOIN channels ch ON ch.sasi_channel_id = e.channel_id
        LEFT JOIN current_status cs ON cs.sasi_event_id = e.id
        ORDER BY e.created_at DESC
    """
    df = pd.read_sql(query, engine)
    engine.dispose()

    df["secretaria"] = df["channel_id"].map(SECRETARIAS_MAP).fillna("Outro")
    df["current_status"] = df["current_status"].map(STATUS_MAP).fillna(df["current_status"])
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True).dt.tz_localize(None)
    df["closed_at"] = pd.to_datetime(df["closed_at"], utc=True).dt.tz_localize(None)
    df["tempo_conclusao"] = df["closed_at"] - df["created_at"]
    df["ano_mes"] = df["created_at"].dt.to_period("M").astype(str)

    return df


def get_downloads_data():
    engine = create_engine(DB_URL)
    query = """
        SELECT
            id,
            nome,
            email,
            telefone,
            status,
            app_id,
            app_nome
        FROM master_users_sasi_pro
    """
    df = pd.read_sql(query, engine)
    engine.dispose()
    return df


df_global = get_data()
df_downloads_global = get_downloads_data()


def render_alertas_tab():
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        className="filter-label", children="Período Início"
                                    ),
                                    dcc.DatePickerSingle(
                                        id="start-date",
                                        date=datetime(2025, 8, 13),
                                        display_format="DD/MM/YYYY",
                                    ),
                                ],
                                className="filter-group",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        className="filter-label", children="Período Fim"
                                    ),
                                    dcc.DatePickerSingle(
                                        id="end-date",
                                        date=datetime(2026, 5, 7),
                                        display_format="DD/MM/YYYY",
                                    ),
                                ],
                                className="filter-group",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        className="filter-label", children="Secretaria"
                                    ),
                                    dcc.Dropdown(
                                        id="secretaria-dropdown",
                                        multi=True,
                                        placeholder="Todas",
                                        style={"minWidth": "200px"},
                                    ),
                                ],
                                className="filter-group",
                            ),
                            html.Div(
                                [
                                    html.Div(className="filter-label", children="Status"),
                                    dcc.Dropdown(
                                        id="status-dropdown",
                                        multi=True,
                                        placeholder="Todos",
                                        style={"minWidth": "200px"},
                                    ),
                                ],
                                className="filter-group",
                            ),
                            html.Button(
                                "🔄 Atualizar",
                                id="refresh-btn",
                                n_clicks=0,
                                className="refresh-btn",
                            ),
                            html.Button(
                                "🗑️ Limpar",
                                id="clear-btn",
                                n_clicks=0,
                                className="clear-btn",
                            ),
                        ],
                        className="filter-row",
                    ),
                ],
                className="filter-section",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(className="metric-icon", children="📊"),
                                    html.Div(
                                        className="metric-label",
                                        children="Total de Alertas",
                                    ),
                                ],
                                className="metric-header",
                            ),
                            html.Div(
                                className="metric-value", id="total-alertas", children="0"
                            ),
                        ],
                        className="metric-card",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(className="metric-icon", children="✅"),
                                    html.Div(
                                        className="metric-label", children="Concluídos"
                                    ),
                                ],
                                className="metric-header",
                            ),
                            html.Div(
                                className="metric-value gold", id="concluidos", children="0"
                            ),
                        ],
                        className="metric-card gold",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(className="metric-icon", children="🏆"),
                                    html.Div(
                                        className="metric-label",
                                        children="Secretaria Líder",
                                    ),
                                ],
                                className="metric-header",
                            ),
                            html.Div(
                                className="metric-value gold",
                                id="secretaria-lider",
                                children="-",
                            ),
                        ],
                        className="metric-card gold",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(className="metric-icon", children="⏱️"),
                                    html.Div(
                                        className="metric-label", children="Tempo Médio de Conclusão"
                                    ),
                                ],
                                className="metric-header",
                            ),
                            html.Div(
                                className="metric-value gold",
                                id="tempo-conclusao",
                                children="0d 0h",
                            ),
                        ],
                        className="metric-card gold",
                    ),
                ],
                className="metrics-grid",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H3("Alertas por Secretaria", className="section-title"),
                            dcc.Graph(id="grafico-secretaria"),
                        ],
                        className="chart-container",
                    ),
                    html.Div(
                        [
                            html.H3("Distribuição por Status", className="section-title"),
                            dcc.Graph(id="grafico-status"),
                        ],
                        className="chart-container",
                    ),
                ],
                className="charts-row",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H3("Ranking de Secretarias", className="section-title"),
                            html.Div(id="ranking-secretarias"),
                        ],
                        className="ranking-card",
                    ),
                    html.Div(
                        [
                            html.H3("Tabela Detalhada", className="section-title"),
                            html.Div(id="tabela-detalhada"),
                        ],
                        className="table-card",
                    ),
                ],
                className="bottom-row",
            ),
            dcc.Store(id="df-store"),
        ]
    )


def render_downloads_tab():
    app_options = [
        {"label": a, "value": a}
        for a in sorted(df_downloads_global["app_nome"].dropna().unique())
    ]

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        className="filter-label", children="Aplicativo"
                                    ),
                                    dcc.Dropdown(
                                        id="app-dropdown",
                                        options=app_options,
                                        multi=True,
                                        placeholder="Todos",
                                        style={"minWidth": "260px"},
                                    ),
                                ],
                                className="filter-group",
                            ),
                            html.Button(
                                "🔄 Atualizar",
                                id="downloads-refresh-btn",
                                n_clicks=0,
                                className="refresh-btn",
                            ),
                            html.Button(
                                "🗑️ Limpar",
                                id="downloads-clear-btn",
                                n_clicks=0,
                                className="clear-btn",
                            ),
                        ],
                        className="filter-row",
                    ),
                ],
                className="filter-section",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(className="metric-icon", children="📲"),
                                    html.Div(
                                        className="metric-label",
                                        children="Total de Downloads",
                                    ),
                                ],
                                className="metric-header",
                            ),
                            html.Div(
                                className="metric-value",
                                id="total-downloads",
                                children="0",
                            ),
                        ],
                        className="metric-card",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(className="metric-icon", children="👤"),
                                    html.Div(
                                        className="metric-label",
                                        children="Usuários Únicos",
                                    ),
                                ],
                                className="metric-header",
                            ),
                            html.Div(
                                className="metric-value gold",
                                id="usuarios-unicos",
                                children="0",
                            ),
                        ],
                        className="metric-card gold",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(className="metric-icon", children="🏆"),
                                    html.Div(
                                        className="metric-label", children="App Líder"
                                    ),
                                ],
                                className="metric-header",
                            ),
                            html.Div(
                                className="metric-value gold",
                                id="app-lider",
                                children="-",
                            ),
                        ],
                        className="metric-card gold",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(className="metric-icon", children="📱"),
                                    html.Div(
                                        className="metric-label",
                                        children="Aplicativos Monitorados",
                                    ),
                                ],
                                className="metric-header",
                            ),
                            html.Div(
                                className="metric-value gold",
                                id="total-apps",
                                children="0",
                            ),
                        ],
                        className="metric-card gold",
                    ),
                ],
                className="metrics-grid",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H3(
                                "Downloads por Aplicativo", className="section-title"
                            ),
                            dcc.Graph(id="grafico-downloads-app"),
                        ],
                        className="chart-container",
                    ),
                    html.Div(
                        [
                            html.H3(
                                "Participação por Aplicativo", className="section-title"
                            ),
                            dcc.Graph(id="grafico-downloads-pie"),
                        ],
                        className="chart-container",
                    ),
                ],
                className="charts-row",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H3(
                                "Ranking de Aplicativos", className="section-title"
                            ),
                            html.Div(id="ranking-downloads"),
                        ],
                        className="ranking-card",
                    ),
                ],
                className="ranking-row",
            ),
        ]
    )


app.layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    [
                        html.H1("Prefeitura Municipal de Envira"),
                        html.P("Dashboard"),
                    ],
                    className="header-content",
                ),
                html.Img(src="/assets/logo-envira.webp", className="header-logo"),
            ],
            className="header",
        ),
        dcc.Tabs(
            id="main-tabs",
            value="tab-alertas",
            className="main-tabs",
            children=[
                dcc.Tab(
                    label="Alertas",
                    value="tab-alertas",
                    className="main-tab",
                    selected_className="main-tab--selected",
                ),
                dcc.Tab(
                    label="Downloads do App",
                    value="tab-downloads",
                    className="main-tab",
                    selected_className="main-tab--selected",
                ),
            ],
        ),
        html.Div(id="tabs-content"),
    ]
)


@callback(
    Output("tabs-content", "children"),
    Input("main-tabs", "value"),
)
def render_tab_content(tab):
    if tab == "tab-downloads":
        return render_downloads_tab()
    return render_alertas_tab()


@callback(
    Output("secretaria-dropdown", "options"),
    Output("status-dropdown", "options"),
    Input("df-store", "data"),
)
def update_dropdowns(data):
    secretarias = [
        {"label": s, "value": s} for s in sorted(df_global["secretaria"].unique())
    ]
    status = [
        {"label": s, "value": s}
        for s in sorted(df_global["current_status"].dropna().unique())
    ]
    return secretarias, status


@callback(
    Output("df-store", "data"),
    Output("total-alertas", "children"),
    Output("concluidos", "children"),
    Output("secretaria-lider", "children"),
    Output("tempo-conclusao", "children"),
    Output("grafico-secretaria", "figure"),
    Output("grafico-status", "figure"),
    Output("ranking-secretarias", "children"),
    Output("tabela-detalhada", "children"),
    Output("start-date", "date"),
    Output("end-date", "date"),
    Output("secretaria-dropdown", "value"),
    Output("status-dropdown", "value"),
    Input("start-date", "date"),
    Input("end-date", "date"),
    Input("secretaria-dropdown", "value"),
    Input("status-dropdown", "value"),
    Input("df-store", "data"),
    Input("refresh-btn", "n_clicks"),
    Input("clear-btn", "n_clicks"),
)
def update_dashboard(start_date, end_date, secretarias, status, data, n_clicks, clear_n_clicks):
    ctx = dash.callback_context
    if ctx.triggered:
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger_id == "clear-btn":
            return "0", "0", "-", "0d 0h", {}, {}, [], None, None, None, None, None

    df = df_global.copy()

    if start_date:
        df = df[df["created_at"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["created_at"] <= pd.to_datetime(end_date)]
    if secretarias:
        df = df[df["secretaria"].isin(secretarias)]
    if status:
        df = df[df["current_status"].isin(status)]

    total_alertas = len(df)
    concluidos = len(df[df["current_status"] == STATUS_CONCLUIDO])

    df_completed = df[df["current_status"] == STATUS_CONCLUIDO].dropna(subset=["tempo_conclusao"])
    if len(df_completed) > 0:
        avg_timedelta = df_completed["tempo_conclusao"].mean()
        days = avg_timedelta.days
        hours = avg_timedelta.seconds // 3600
        tempo_conclusao = f"{days}d {hours}h"
    else:
        tempo_conclusao = "0d 0h"

    ranking = (
        df.groupby("secretaria")
        .size()
        .reset_index(name="total")
        .sort_values("total", ascending=False)
    )
    secretaria_lider = ranking.iloc[0]["secretaria"] if len(ranking) > 0 else "-"

    fig_bar = px.bar(
        ranking,
        x="secretaria",
        y="total",
        color="total",
        color_continuous_scale=[[0, "#e8f5ec"], [1, "#14622C"]],
        text_auto=True,
    )
    fig_bar.update_layout(
        showlegend=False,
        xaxis_title="",
        yaxis_title="Quantidade",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(color="#4a5568")),
        yaxis=dict(tickfont=dict(color="#4a5568")),
        font=dict(family="Inter"),
    )
    fig_bar.update_traces(marker=dict(line=dict(width=0)), textposition='outside')

    status_counts = df["current_status"].value_counts().reset_index()
    status_counts.columns = ["status", "total"]
    fig_pie = px.pie(
        status_counts.head(8),
        values="total",
        names="status",
        hole=0.5,
        color_discrete_sequence=CHART_COLOR_PALETTE,
    )
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.5,
            xanchor="left",
            x=1.02
        ),
        margin=dict(t=20, b=20, l=20, r=120),
    )
    fig_pie.update_traces(
        textinfo="label+value",
        texttemplate="%{label}: %{value}"
    )

    ranking_html = []
    for i, row in ranking.reset_index(drop=True).iterrows():
        ranking_html.append(
            html.Div(
                [
                    html.Span(f"#{i+1}", className="rank"),
                    html.Span(row["secretaria"], className="name"),
                    html.Span(str(row["total"]), className="value"),
                ],
                className="ranking-item",
            )
        )

    df_table = df[["alert_id", "created_at", "channel_name", "secretaria", "current_status"]].copy()
    df_table["data"] = df_table["created_at"].dt.strftime("%d/%m/%Y")
    df_table["hora"] = df_table["created_at"].dt.strftime("%H:%M")
    df_table = df_table[["alert_id", "data", "hora", "channel_name", "secretaria", "current_status"]]
    df_table.columns = ["Protocolo", "Data", "Hora", "Canal", "Secretaria", "Status"]
    table = dash_table.DataTable(
        data=df_table.head(50).to_dict("records"),
        columns=[{"name": c, "id": c} for c in df_table.columns],
        page_size=15,
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": "#14622C",
            "color": "white",
            "fontWeight": "600",
            "padding": "12px",
            "textAlign": "left",
        },
        style_cell={
            "padding": "10px 12px",
            "color": "#4a5568",
            "borderBottom": "1px solid #e2e8f0",
        },
        style_data={
            "backgroundColor": "#ffffff",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f7fafc"},
        ],
    )

    return (
        {},
        total_alertas,
        concluidos,
        secretaria_lider,
        tempo_conclusao,
        fig_bar,
        fig_pie,
        ranking_html,
        table,
        dash.no_update,
        dash.no_update,
        dash.no_update,
        dash.no_update,
    )


@callback(
    Output("total-downloads", "children"),
    Output("usuarios-unicos", "children"),
    Output("app-lider", "children"),
    Output("total-apps", "children"),
    Output("grafico-downloads-app", "figure"),
    Output("grafico-downloads-pie", "figure"),
    Output("ranking-downloads", "children"),
    Output("app-dropdown", "value"),
    Input("app-dropdown", "value"),
    Input("downloads-refresh-btn", "n_clicks"),
    Input("downloads-clear-btn", "n_clicks"),
)
def update_downloads_dashboard(apps_selecionados, n_clicks, clear_n_clicks):
    global df_downloads_global

    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    if trigger_id == "downloads-clear-btn":
        apps_selecionados = None

    if trigger_id == "downloads-refresh-btn":
        try:
            requests.get(USERS_SYNC_URL, timeout=30)
        except requests.RequestException:
            pass
        df_downloads_global = get_downloads_data()

    df = df_downloads_global.copy()

    if apps_selecionados:
        df = df[df["app_nome"].isin(apps_selecionados)]

    total_downloads = len(df)
    usuarios_unicos = df["email"].nunique()
    total_apps = df["app_nome"].nunique()

    ranking = (
        df.groupby("app_nome")
        .size()
        .reset_index(name="total")
        .sort_values("total", ascending=False)
    )
    app_lider = ranking.iloc[0]["app_nome"] if len(ranking) > 0 else "-"

    fig_bar = px.bar(
        ranking,
        x="app_nome",
        y="total",
        color="total",
        color_continuous_scale=[[0, "#e8f5ec"], [1, "#14622C"]],
        text_auto=True,
    )
    fig_bar.update_layout(
        showlegend=False,
        xaxis_title="",
        yaxis_title="Downloads",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(color="#4a5568")),
        yaxis=dict(tickfont=dict(color="#4a5568")),
        font=dict(family="Inter"),
    )
    fig_bar.update_traces(marker=dict(line=dict(width=0)), textposition="outside")

    fig_pie = px.pie(
        ranking,
        values="total",
        names="app_nome",
        hole=0.5,
        color_discrete_sequence=CHART_COLOR_PALETTE,
    )
    fig_pie.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="v", yanchor="top", y=0.5, xanchor="left", x=1.02),
        margin=dict(t=20, b=20, l=20, r=120),
        font=dict(family="Inter"),
    )
    fig_pie.update_traces(textinfo="label+value", texttemplate="%{label}: %{value}")

    ranking_html = []
    for i, row in ranking.reset_index(drop=True).iterrows():
        ranking_html.append(
            html.Div(
                [
                    html.Span(f"#{i+1}", className="rank"),
                    html.Span(row["app_nome"], className="name"),
                    html.Span(str(row["total"]), className="value"),
                ],
                className="ranking-item",
            )
        )

    dropdown_value = None if trigger_id == "downloads-clear-btn" else dash.no_update

    return (
        total_downloads,
        usuarios_unicos,
        app_lider,
        total_apps,
        fig_bar,
        fig_pie,
        ranking_html,
        dropdown_value,
    )


if __name__ == "__main__":
    app.run(port=8050)
