"""
gerar_dashboard.py
Gera dashboard.html com dados reais do SQLite (ou dados de exemplo se banco vazio).
Execute: python gerar_dashboard.py
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "tickets.db")
OUT_PATH = os.path.join(os.path.dirname(__file__), "dashboard.html")

def carregar_dados():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM tickets ORDER BY timestamp DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []

def dados_exemplo():
    """Retorna dados de exemplo realistas para demonstração."""
    hoje = datetime.now().date().isoformat()
    ontem = (datetime.now() - timedelta(days=1)).date().isoformat()
    setores = ["Fiscal", "Folha", "Balanço", "Administração", "Triagem", "Geral"]
    colaboradores = [
        "Colaborador 3", "Colaborador 4", "Colaborador 5", "Colaborador 6",
        "Colaborador 7", "Colaborador 8", "Colaborador 9", "Colaborador 10",
        "Colaborador 11", "Colaborador 12"
    ]
    clientes = [
        "Empresa Alpha", "Construtora Beta", "Ind. Gama", "Com. Delta",
        "Serv. Epsilon", "Agro Zeta", "Tech Eta", "Med. Theta",
        "Edu. Iota", "Log. Kappa", "Farm. Lambda", "Auto Mu"
    ]
    tickets = []
    import random
    random.seed(42)
    periodos = [("Manhã", 8, 12), ("Tarde", 13, 17), ("Noite", 18, 22)]

    for i in range(1, 89):
        setor = random.choice(setores)
        colab = random.choice(colaboradores)
        cliente = random.choice(clientes)
        periodo_name, h_min, h_max = random.choice(periodos)
        hora = random.randint(h_min, h_max)
        data = hoje if i <= 55 else ontem
        # alguns tickets abertos há mais de 2h
        if i % 5 == 0:
            ts = (datetime.now() - timedelta(hours=random.uniform(2.5, 10))).isoformat()
            status = "aberto"
        elif i % 3 == 0:
            ts = (datetime.now() - timedelta(hours=random.uniform(0.5, 2))).isoformat()
            status = "aberto"
        else:
            ts = (datetime.now() - timedelta(hours=random.uniform(0, 8))).isoformat()
            status = "fechado"
        tickets.append({
            "ticket_id": str(1000 + i),
            "numero": str(1000 + i),
            "colaborador": colab,
            "setor": setor,
            "cliente": cliente,
            "solicitante": cliente,
            "status": status,
            "prioridade": random.choice(["normal", "alta", "urgente"]),
            "descricao": f"Ticket #{1000 + i}",
            "timestamp": ts,
            "hora": hora,
            "periodo": periodo_name,
            "data": data,
            "alerta_enviado": 0,
        })
    return tickets

def calcular_metricas(tickets):
    hoje = datetime.now().date().isoformat()
    agora = datetime.now()

    tickets_hoje = [t for t in tickets if t.get("data", "") == hoje or
                    t.get("timestamp", "").startswith(hoje)]
    tickets_abertos = [t for t in tickets if t.get("status") == "aberto"]
    total = len(tickets)

    # Tickets abertos > 2h
    atrasados = []
    for t in tickets_abertos:
        try:
            ts = datetime.fromisoformat(t["timestamp"])
            diff = (agora - ts).total_seconds() / 3600
            if diff > 2:
                horas = round(diff, 1)
                t2 = dict(t)
                t2["horas_aberto"] = horas
                if horas > 8:
                    t2["nivel"] = "critico"
                elif horas > 4:
                    t2["nivel"] = "alto"
                else:
                    t2["nivel"] = "medio"
                atrasados.append(t2)
        except Exception:
            pass
    atrasados.sort(key=lambda x: x["horas_aberto"], reverse=True)

    # Por setor
    por_setor = defaultdict(int)
    for t in tickets_hoje or tickets:
        por_setor[t.get("setor", "?")] += 1
    por_setor = dict(sorted(por_setor.items(), key=lambda x: x[1], reverse=True))

    # Top colaboradores
    por_colab = defaultdict(int)
    for t in tickets:
        por_colab[t.get("colaborador", "?")] += 1
    top_colab = dict(sorted(por_colab.items(), key=lambda x: x[1], reverse=True)[:10])

    # Top clientes
    por_cliente = defaultdict(int)
    for t in tickets_hoje or tickets:
        por_cliente[t.get("cliente", "?")] += 1
    top_clientes = dict(sorted(por_cliente.items(), key=lambda x: x[1], reverse=True)[:10])

    # Por período
    por_periodo = {"Manhã": 0, "Tarde": 0, "Noite": 0}
    for t in tickets:
        p = t.get("periodo", "")
        if p in por_periodo:
            por_periodo[p] += 1

    setor_maior = max(por_setor, key=por_setor.get) if por_setor else "-"
    colab_maior = max(por_colab, key=por_colab.get) if por_colab else "-"

    return {
        "total_hoje": len(tickets_hoje),
        "total_abertos": len(tickets_abertos),
        "total_acumulado": total,
        "total_atrasados": len(atrasados),
        "setor_maior_volume": setor_maior,
        "colaborador_maior_volume": colab_maior,
        "por_setor": por_setor,
        "top_colab": top_colab,
        "top_clientes": top_clientes,
        "por_periodo": por_periodo,
        "atrasados": atrasados[:20],
        "gerado_em": agora.strftime("%d/%m/%Y %H:%M"),
    }

def gerar_html(m):
    dados_json = json.dumps(m, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Dashboard Exemplo</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',system-ui,sans-serif;background:#F8FAFC;color:#1F2937;min-height:100vh}}
  .topbar{{background:#14532D;color:#fff;padding:14px 28px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(0,0,0,.25)}}
  .topbar h1{{font-size:1.25rem;font-weight:700;letter-spacing:.3px}}
  .topbar .meta{{font-size:.8rem;opacity:.75}}
  .content{{padding:20px 24px;display:flex;flex-direction:column;gap:20px}}

  /* KPIs */
  .kpi-row{{display:grid;grid-template-columns:repeat(6,1fr);gap:14px}}
  .kpi{{background:#14532D;color:#fff;border-radius:12px;padding:20px 16px;display:flex;flex-direction:column;gap:6px;box-shadow:0 2px 8px rgba(20,83,45,.3)}}
  .kpi .val{{font-size:2.4rem;font-weight:800;line-height:1}}
  .kpi .lbl{{font-size:.75rem;text-transform:uppercase;letter-spacing:.6px;opacity:.8}}
  .kpi.accent{{background:#22C55E;color:#052e16}}
  .kpi.warn{{background:#F59E0B;color:#1F2937}}

  /* Charts row */
  .row-2{{display:grid;grid-template-columns:3fr 2fr;gap:16px}}
  .row-3{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
  .card{{background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
  .card h2{{font-size:.9rem;font-weight:700;color:#14532D;margin-bottom:14px;text-transform:uppercase;letter-spacing:.4px;border-bottom:2px solid #22C55E;padding-bottom:6px}}
  .chart-wrap{{position:relative;width:100%;height:260px}}
  .chart-wrap-tall{{position:relative;width:100%;height:300px}}

  /* Table */
  table{{width:100%;border-collapse:collapse;font-size:.85rem}}
  thead th{{background:#14532D;color:#fff;padding:10px 12px;text-align:left;font-size:.78rem;letter-spacing:.3px;text-transform:uppercase}}
  tbody tr:nth-child(even){{background:#F0FDF4}}
  tbody td{{padding:9px 12px;border-bottom:1px solid #E5E7EB}}
  tbody tr:hover{{background:#DCFCE7}}

  /* Alert rows */
  .nivel-medio td{{background:#FEF9C3!important;border-left:4px solid #F59E0B}}
  .nivel-alto td{{background:#FFEDD5!important;border-left:4px solid #F97316}}
  .nivel-critico td{{background:#FEE2E2!important;border-left:4px solid #DC2626}}
  .nivel-medio:hover td,.nivel-alto:hover td,.nivel-critico:hover td{{filter:brightness(.96)}}

  .badge{{display:inline-block;padding:2px 8px;border-radius:99px;font-size:.72rem;font-weight:700}}
  .badge-m{{background:#FEF9C3;color:#92400E}}
  .badge-a{{background:#FFEDD5;color:#9A3412}}
  .badge-c{{background:#FEE2E2;color:#991B1B}}

  @media(max-width:900px){{
    .kpi-row{{grid-template-columns:repeat(3,1fr)}}
    .row-2,.row-3{{grid-template-columns:1fr}}
  }}
</style>
</head>
<body>
<div class="topbar">
  <h1>📊 Dashboard Exemplo</h1>
  <span class="meta">Atualizado em: {m['gerado_em']} &nbsp;|&nbsp; Fonte: Zendesk via Slack</span>
</div>
<div class="content">

  <!-- LINHA 1: KPIs -->
  <div class="kpi-row">
    <div class="kpi">
      <span class="val">{m['total_hoje']}</span>
      <span class="lbl">Tickets Hoje</span>
    </div>
    <div class="kpi">
      <span class="val">{m['total_abertos']}</span>
      <span class="lbl">Tickets Pendentes</span>
    </div>
    <div class="kpi">
      <span class="val">{m['total_acumulado']}</span>
      <span class="lbl">Total Acumulado</span>
    </div>
    <div class="kpi warn">
      <span class="val">{m['total_atrasados']}</span>
      <span class="lbl">Tickets &gt; 2h</span>
    </div>
    <div class="kpi accent">
      <span class="val" style="font-size:1.1rem;padding-top:4px">{m['setor_maior_volume']}</span>
      <span class="lbl">Setor com Maior Volume</span>
    </div>
    <div class="kpi" style="background:#166534">
      <span class="val" style="font-size:.95rem;padding-top:4px">{m['colaborador_maior_volume'].split()[0]}</span>
      <span class="lbl">Top Colaborador</span>
    </div>
  </div>

  <!-- LINHA 2: Bar + Pie -->
  <div class="row-2">
    <div class="card">
      <h2>Tickets por Setor</h2>
      <div class="chart-wrap"><canvas id="chartSetor"></canvas></div>
    </div>
    <div class="card">
      <h2>Distribuição por Setor (%)</h2>
      <div class="chart-wrap"><canvas id="chartPie"></canvas></div>
    </div>
  </div>

  <!-- LINHA 3: Colaboradores + Período -->
  <div class="row-3">
    <div class="card">
      <h2>Top 10 Colaboradores</h2>
      <div class="chart-wrap-tall"><canvas id="chartColab"></canvas></div>
    </div>
    <div class="card">
      <h2>Tickets por Período</h2>
      <div class="chart-wrap-tall"><canvas id="chartPeriodo"></canvas></div>
    </div>
  </div>

  <!-- LINHA 4: Top Clientes -->
  <div class="card">
    <h2>Top Clientes do Dia</h2>
    <table>
      <thead><tr><th>#</th><th>Cliente</th><th>Quantidade de Tickets</th></tr></thead>
      <tbody id="tblClientes"></tbody>
    </table>
  </div>

  <!-- LINHA 5: Tickets atrasados -->
  <div class="card">
    <h2>⚠️ Monitoramento Operacional — Tickets com &gt; 2h em Aberto</h2>
    <table>
      <thead>
        <tr>
          <th>Ticket</th><th>Colaborador</th><th>Setor</th>
          <th>Cliente</th><th>Tempo Aberto</th><th>Nível</th>
        </tr>
      </thead>
      <tbody id="tblAtrasados"></tbody>
    </table>
  </div>

</div>
<script>
const D = {dados_json};

// Paleta
const verde = '#14532D', verde2 = '#22C55E', cinza = '#6B7280';
const palette = ['#14532D','#166534','#15803D','#16A34A','#22C55E','#4ADE80',
                 '#86EFAC','#BBF7D0','#F59E0B','#DC2626'];

// Chart: Setor (barras horizontais)
new Chart(document.getElementById('chartSetor'), {{
  type: 'bar',
  data: {{
    labels: Object.keys(D.por_setor),
    datasets: [{{ label: 'Tickets', data: Object.values(D.por_setor),
      backgroundColor: palette, borderRadius: 6, borderSkipped: false }}]
  }},
  options: {{
    indexAxis: 'y', responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: c => ` ${{c.parsed.x}} tickets` }} }} }},
    scales: {{
      x: {{ grid: {{ color:'#E5E7EB' }}, ticks: {{ color: '#1F2937' }} }},
      y: {{ grid: {{ display: false }}, ticks: {{ color: '#1F2937', font: {{ size: 12 }} }} }}
    }}
  }}
}});

// Chart: Pie
new Chart(document.getElementById('chartPie'), {{
  type: 'doughnut',
  data: {{
    labels: Object.keys(D.por_setor),
    datasets: [{{ data: Object.values(D.por_setor), backgroundColor: palette,
      borderWidth: 2, borderColor: '#F8FAFC' }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'bottom', labels: {{ font: {{ size: 12 }} }} }} }}
  }}
}});

// Chart: Top Colaboradores
new Chart(document.getElementById('chartColab'), {{
  type: 'bar',
  data: {{
    labels: Object.keys(D.top_colab),
    datasets: [{{ label: 'Tickets', data: Object.values(D.top_colab),
      backgroundColor: '#14532D', borderRadius: 6, borderSkipped: false }}]
  }},
  options: {{
    indexAxis: 'y', responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: {{ color:'#E5E7EB' }}, ticks: {{ color: '#1F2937' }} }},
      y: {{ grid: {{ display: false }}, ticks: {{ color: '#1F2937', font: {{ size: 11 }} }} }}
    }}
  }}
}});

// Chart: Período
new Chart(document.getElementById('chartPeriodo'), {{
  type: 'bar',
  data: {{
    labels: Object.keys(D.por_periodo),
    datasets: [{{ label: 'Tickets', data: Object.values(D.por_periodo),
      backgroundColor: ['#22C55E','#14532D','#166534'],
      borderRadius: 8, borderSkipped: false }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: c => ` ${{c.parsed.y}} tickets` }} }} }},
    scales: {{
      x: {{ grid: {{ display: false }}, ticks: {{ color: '#1F2937', font: {{ size: 13 }} }} }},
      y: {{ grid: {{ color:'#E5E7EB' }}, ticks: {{ color: '#1F2937' }} }}
    }}
  }}
}});

// Tabela Clientes
const tblC = document.getElementById('tblClientes');
Object.entries(D.top_clientes).forEach(([k,v], i) => {{
  tblC.innerHTML += `<tr><td>${{i+1}}</td><td>${{k}}</td><td><strong>${{v}}</strong></td></tr>`;
}});

// Tabela Atrasados
const tblA = document.getElementById('tblAtrasados');
if (!D.atrasados.length) {{
  tblA.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;color:#6B7280">✅ Nenhum ticket atrasado</td></tr>';
}} else {{
  D.atrasados.forEach(t => {{
    const badges = {{medio:'badge-m',alto:'badge-a',critico:'badge-c'}};
    const labels = {{medio:'⚠️ +2h',alto:'🟠 +4h',critico:'🔴 +8h'}};
    tblA.innerHTML += `
      <tr class="nivel-${{t.nivel}}">
        <td>#${{t.numero}}</td>
        <td>${{t.colaborador}}</td>
        <td>${{t.setor}}</td>
        <td>${{t.cliente}}</td>
        <td>${{t.horas_aberto}}h</td>
        <td><span class="badge ${{badges[t.nivel]}}">${{labels[t.nivel]}}</span></td>
      </tr>`;
  }});
}}
</script>
</body>
</html>"""
    return html

if __name__ == "__main__":
    tickets = carregar_dados()
    if not tickets:
        print("⚠️  Banco vazio — usando dados de exemplo para demonstração.")
        tickets = dados_exemplo()
    m = calcular_metricas(tickets)
    html = gerar_html(m)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Dashboard gerado: {OUT_PATH}")
    print(f"   Tickets: {m['total_acumulado']} | Hoje: {m['total_hoje']} | Pendentes: {m['total_abertos']}")
