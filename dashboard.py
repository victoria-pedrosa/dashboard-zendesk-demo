import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from database import buscar_todos, criar_banco
from metrics import calcular_metricas
from collector import coletar_mensagens
from config import CORES

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Zendesk | Exemplo",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS Exemplo ──────────────────────────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    .stApp {{
        background-color: {CORES['cinza']};
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: {CORES['verde_escuro']};
    }}
    section[data-testid="stSidebar"] * {{
        color: white !important;
    }}
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stDateInput label {{
        color: {CORES['verde_claro']} !important;
        font-weight: 600;
    }}

    /* Cards de métricas */
    .card {{
        background: white;
        border-radius: 12px;
        padding: 20px 24px;
        border-left: 5px solid {CORES['verde_medio']};
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin-bottom: 8px;
    }}
    .card-title {{
        color: {CORES['verde_escuro']};
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }}
    .card-value {{
        color: {CORES['texto']};
        font-size: 32px;
        font-weight: 700;
        line-height: 1;
    }}
    .card-sub {{
        color: #888;
        font-size: 12px;
        margin-top: 4px;
    }}
    .card-destaque {{
        border-left-color: {CORES['verde_claro']};
    }}

    /* Header */
    .header {{
        background: linear-gradient(135deg, {CORES['verde_escuro']} 0%, {CORES['verde_medio']} 100%);
        border-radius: 12px;
        padding: 20px 28px;
        margin-bottom: 24px;
        color: white;
    }}
    .header h1 {{
        color: white;
        font-size: 24px;
        font-weight: 700;
        margin: 0;
    }}
    .header p {{
        color: rgba(255,255,255,0.7);
        margin: 4px 0 0 0;
        font-size: 14px;
    }}

    /* Seção */
    .secao {{
        background: white;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}
    .secao-titulo {{
        color: {CORES['verde_escuro']};
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 2px solid {CORES['verde_suave']};
    }}

    /* Botão de atualizar */
    .stButton > button {{
        background-color: {CORES['verde_medio']};
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 20px;
        width: 100%;
    }}
    .stButton > button:hover {{
        background-color: {CORES['verde_escuro']};
    }}

    /* Remove padding padrão do streamlit */
    .block-container {{
        padding-top: 1rem;
    }}
</style>
""", unsafe_allow_html=True)

# ── Init banco ──────────────────────────────────────────────────────────────
criar_banco()

# ── Sidebar — Filtros ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Dashboard Zendesk")
    st.markdown("**Escritório Contábil Exemplo**")
    st.divider()

    if st.button("🔄 Atualizar dados agora"):
        with st.spinner("Coletando..."):
            novos = coletar_mensagens()
        st.success(f"✅ {novos} tickets novos")

    st.markdown("### Filtros")

    data_inicio = st.date_input("Data início", date.today() - timedelta(days=30))
    data_fim = st.date_input("Data fim", date.today())

    df_raw = buscar_todos()

    colaboradores = ["Todos"] + sorted(df_raw["colaborador"].dropna().unique().tolist()) if not df_raw.empty else ["Todos"]
    colaborador_sel = st.selectbox("Colaborador", colaboradores)

    clientes = ["Todos"] + sorted(df_raw["cliente"].dropna().unique().tolist()) if not df_raw.empty else ["Todos"]
    cliente_sel = st.selectbox("Cliente", clientes)

    status_opts = ["Todos", "aberto", "resolvido"]
    status_sel = st.selectbox("Status", status_opts)

    periodos = ["Todos", "Manhã", "Tarde", "Noite", "Madrugada"]
    periodo_sel = st.selectbox("Período do dia", periodos)

    setores = ["Todos"] + sorted(df_raw["setor"].dropna().unique().tolist()) if not df_raw.empty else ["Todos"]
    setor_sel = st.selectbox("Setor", setores)

    st.divider()
    st.caption("Atualização automática a cada 5 min")

# ── Aplica filtros ──────────────────────────────────────────────────────────
df = df_raw.copy() if not df_raw.empty else pd.DataFrame()

if not df.empty:
    df["data"] = pd.to_datetime(df["data"])
    df = df[(df["data"] >= pd.Timestamp(data_inicio)) & (df["data"] <= pd.Timestamp(data_fim))]

    if colaborador_sel != "Todos":
        df = df[df["colaborador"] == colaborador_sel]
    if cliente_sel != "Todos":
        df = df[df["cliente"] == cliente_sel]
    if status_sel != "Todos":
        df = df[df["status"] == status_sel]
    if periodo_sel != "Todos":
        df = df[df["periodo"] == periodo_sel]
    if setor_sel != "Todos":
        df = df[df["setor"] == setor_sel]

    df["data"] = df["data"].dt.strftime("%Y-%m-%d")

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="header">
    <h1>📊 Dashboard Zendesk</h1>
    <p>Escritório Contábil Exemplo · Atualizado automaticamente</p>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("⚠️ Nenhum dado encontrado. Clique em 'Atualizar dados agora' na barra lateral.")
    st.stop()

# ── Métricas principais ─────────────────────────────────────────────────────
hoje = str(date.today())
df_hoje = df[df["data"] == hoje] if not df.empty else pd.DataFrame()

total = len(df)
total_hoje = len(df_hoje)
resolvidos = len(df_hoje[df_hoje["status"] == "resolvido"]) if not df_hoje.empty else 0
pendentes = len(df_hoje[df_hoje["status"] == "aberto"]) if not df_hoje.empty else 0
taxa = round(resolvidos / total_hoje * 100, 1) if total_hoje > 0 else 0
mais_recebeu = df_hoje["colaborador"].value_counts().index[0] if not df_hoje.empty else "—"

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""<div class="card">
        <div class="card-title">🎫 Tickets Hoje</div>
        <div class="card-value">{total_hoje}</div>
        <div class="card-sub">Total acumulado: {total}</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""<div class="card card-destaque">
        <div class="card-title">✅ Resolvidos Hoje</div>
        <div class="card-value">{resolvidos}</div>
        <div class="card-sub">Taxa: {taxa}%</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""<div class="card">
        <div class="card-title">⏳ Pendentes</div>
        <div class="card-value">{pendentes}</div>
        <div class="card-sub">Em aberto hoje</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""<div class="card">
        <div class="card-title">📈 Taxa de Resolução</div>
        <div class="card-value">{taxa}%</div>
        <div class="card-sub">Hoje</div>
    </div>""", unsafe_allow_html=True)

with col5:
    st.markdown(f"""<div class="card card-destaque">
        <div class="card-title">🏆 Mais Ativos Hoje</div>
        <div class="card-value" style="font-size:20px">{mais_recebeu}</div>
        <div class="card-sub">Maior volume</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Gráficos linha 1 ────────────────────────────────────────────────────────
col_a, col_b = st.columns([3, 2])

VERDE_PALETTE = [CORES["verde_escuro"], CORES["verde_medio"], CORES["verde_claro"], "#7ecf9e", "#a8dfc0"]

with col_a:
    st.markdown('<div class="secao"><div class="secao-titulo">📅 Evolução diária de tickets</div>', unsafe_allow_html=True)
    evolucao = df.groupby("data").size().reset_index(name="tickets")
    fig = px.area(
        evolucao, x="data", y="tickets",
        color_discrete_sequence=[CORES["verde_medio"]],
    )
    fig.update_traces(fillcolor=CORES["verde_suave"], line_color=CORES["verde_escuro"])
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="", yaxis_title="Tickets",
        height=240
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_b:
    st.markdown('<div class="secao"><div class="secao-titulo">⏰ Distribuição por período</div>', unsafe_allow_html=True)
    if not df_hoje.empty:
        periodos_data = df_hoje["periodo"].value_counts().reset_index()
        periodos_data.columns = ["periodo", "count"]
    else:
        periodos_data = pd.DataFrame({"periodo": ["Manhã", "Tarde", "Noite"], "count": [0, 0, 0]})

    fig2 = px.pie(
        periodos_data, names="periodo", values="count",
        color_discrete_sequence=VERDE_PALETTE,
        hole=0.4
    )
    fig2.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=-0.15),
        height=240
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Gráficos linha 2 ────────────────────────────────────────────────────────
col_c, col_d = st.columns(2)

with col_c:
    st.markdown('<div class="secao"><div class="secao-titulo">👥 Ranking de colaboradores</div>', unsafe_allow_html=True)
    rank_colab = df.groupby("colaborador").size().sort_values(ascending=True).tail(10).reset_index(name="tickets")
    fig3 = px.bar(
        rank_colab, x="tickets", y="colaborador", orientation="h",
        color_discrete_sequence=[CORES["verde_medio"]],
        text="tickets"
    )
    fig3.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="", yaxis_title="",
        height=300
    )
    fig3.update_traces(textposition="outside")
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_d:
    st.markdown('<div class="secao"><div class="secao-titulo">🏢 Top clientes</div>', unsafe_allow_html=True)
    rank_cli = df.groupby("cliente").size().sort_values(ascending=True).tail(10).reset_index(name="tickets")
    fig4 = px.bar(
        rank_cli, x="tickets", y="cliente", orientation="h",
        color_discrete_sequence=[CORES["verde_claro"]],
        text="tickets"
    )
    fig4.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="", yaxis_title="",
        height=300
    )
    fig4.update_traces(textposition="outside")
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Gráfico por hora ────────────────────────────────────────────────────────
st.markdown('<div class="secao"><div class="secao-titulo">🕐 Volume de tickets por hora do dia</div>', unsafe_allow_html=True)
por_hora = df.groupby("hora").size().reindex(range(24), fill_value=0).reset_index(name="tickets")
fig5 = px.bar(
    por_hora, x="hora", y="tickets",
    color_discrete_sequence=[CORES["verde_escuro"]],
)
fig5.add_vrect(x0=5.5, x1=11.5, fillcolor=CORES["verde_suave"], opacity=0.3, line_width=0, annotation_text="Manhã")
fig5.add_vrect(x0=11.5, x1=17.5, fillcolor=CORES["verde_claro"], opacity=0.15, line_width=0, annotation_text="Tarde")
fig5.add_vrect(x0=17.5, x1=23.5, fillcolor=CORES["verde_escuro"], opacity=0.1, line_width=0, annotation_text="Noite")
fig5.update_layout(
    plot_bgcolor="white", paper_bgcolor="white",
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(tickmode="linear", dtick=1, title="Hora"),
    yaxis_title="Tickets",
    height=260
)
st.plotly_chart(fig5, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# ── Por setor ───────────────────────────────────────────────────────────────
col_e, col_f = st.columns(2)

with col_e:
    st.markdown('<div class="secao"><div class="secao-titulo">🏷️ Tickets por setor</div>', unsafe_allow_html=True)
    por_setor = df.groupby("setor").size().sort_values(ascending=False).reset_index(name="tickets")
    fig6 = px.bar(
        por_setor, x="setor", y="tickets",
        color_discrete_sequence=VERDE_PALETTE,
        text="tickets"
    )
    fig6.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="", yaxis_title="",
        height=240
    )
    fig6.update_traces(textposition="outside")
    st.plotly_chart(fig6, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_f:
    st.markdown('<div class="secao"><div class="secao-titulo">📋 Status dos tickets</div>', unsafe_allow_html=True)
    por_status = df.groupby("status").size().reset_index(name="tickets")
    fig7 = px.pie(
        por_status, names="status", values="tickets",
        color_discrete_sequence=[CORES["verde_escuro"], CORES["verde_claro"]],
        hole=0.4
    )
    fig7.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=0, t=10, b=0),
        height=240
    )
    st.plotly_chart(fig7, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Tabela detalhada ─────────────────────────────────────────────────────────
st.markdown('<div class="secao"><div class="secao-titulo">📄 Tickets detalhados</div>', unsafe_allow_html=True)
colunas = ["numero", "data", "hora", "periodo", "colaborador", "setor", "cliente", "solicitante", "status", "prioridade"]
df_exibir = df[colunas].rename(columns={
    "numero": "Ticket", "data": "Data", "hora": "Hora", "periodo": "Período",
    "colaborador": "Colaborador", "setor": "Setor", "cliente": "Cliente",
    "solicitante": "Solicitante", "status": "Status", "prioridade": "Prioridade"
}).sort_values("Data", ascending=False)

st.dataframe(df_exibir, use_container_width=True, height=400)
st.markdown('</div>', unsafe_allow_html=True)
