import pandas as pd
from database import buscar_todos, buscar_tickets_abertos_atrasados
from datetime import date

CLIENTES_IGNORADOS = {"Nao identificado", "Escritório Contábil Exemplo", "Nao informado", ""}

def calcular_metricas(df: pd.DataFrame = None) -> dict:
    if df is None:
        df = buscar_todos()

    if df.empty:
        return {"erro": "Sem dados"}

    hoje = str(date.today())
    df_hoje = df[df["data"] == hoje]

    total = len(df)
    total_hoje = len(df_hoje)
    pendentes_hoje = len(df_hoje[df_hoje["status"] == "aberto"])

    # Por periodo
    por_periodo = df_hoje.groupby("periodo").size().to_dict()

    # Por colaborador
    por_colab = df_hoje.groupby("colaborador").size().sort_values(ascending=False)
    top_colaboradores = por_colab.head(10).to_dict()
    mais_recebeu = por_colab.index[0] if not por_colab.empty else "N/A"

    # Por cliente (exclui entradas sem identificacao e a propria empresa)
    df_clientes = df_hoje[~df_hoje["cliente"].isin(CLIENTES_IGNORADOS)]
    top_clientes = df_clientes.groupby("cliente").size().sort_values(ascending=False).head(10).to_dict()

    # Por hora
    por_hora = df_hoje.groupby("hora").size().reindex(range(24), fill_value=0).to_dict()

    # Por setor
    por_setor = df_hoje.groupby("setor").size().sort_values(ascending=False).to_dict()
    por_setor_total = df.groupby("setor").size().sort_values(ascending=False).to_dict()

    # Top 5 colaboradores por setor (hoje)
    top_por_setor = {}
    if not df_hoje.empty and "setor" in df_hoje.columns:
        for setor in df_hoje["setor"].unique():
            df_setor = df_hoje[df_hoje["setor"] == setor]
            ranking = df_setor.groupby("colaborador").size().sort_values(ascending=False).head(5)
            top_por_setor[setor] = ranking.to_dict()

    # Evolucao diaria (ultimos 30 dias)
    evolucao_diaria = df.groupby("data").size().tail(30).to_dict()

    # Evolucao semanal
    df["semana"] = pd.to_datetime(df["data"]).dt.isocalendar().week.astype(str)
    evolucao_semanal = df.groupby("semana").size().tail(8).to_dict()

    # Tickets atrasados (abertos ha mais de 2h)
    tickets_atrasados = buscar_tickets_abertos_atrasados(horas=2)

    return {
        "total": total,
        "total_hoje": total_hoje,
        "pendentes_hoje": pendentes_hoje,
        "mais_recebeu": mais_recebeu,
        "por_periodo": {
            "Manha": por_periodo.get("Manha", 0),
            "Tarde": por_periodo.get("Tarde", 0),
            "Noite": por_periodo.get("Noite", 0),
            "Madrugada": por_periodo.get("Madrugada", 0),
        },
        "top_colaboradores": top_colaboradores,
        "top_clientes": top_clientes,
        "por_hora": por_hora,
        "por_setor": por_setor,
        "por_setor_total": por_setor_total,
        "top_por_setor": top_por_setor,
        "tickets_atrasados": tickets_atrasados,
        "evolucao_diaria": evolucao_diaria,
        "evolucao_semanal": evolucao_semanal,
    }
