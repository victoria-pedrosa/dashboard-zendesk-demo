"""
gerar_pdf.py
Gera relatorio PDF completo do dashboard Zendesk - Exemplo.
"""
import os
import sys
from datetime import date, datetime
from fpdf import FPDF, XPos, YPos

os.makedirs("data", exist_ok=True)

from metrics import calcular_metricas
from database import buscar_tickets_abertos_atrasados

# Paleta Exemplo
VERDE_ESCURO  = (28,  98,  57)   # cabecalhos, titulos
VERDE_CLARO   = (195, 228, 207)  # fundo de secoes
VERDE_BARRA   = (76,  153, 102)  # barras do grafico
VERDE_LINHA   = (230, 245, 235)  # linhas pares da tabela
CINZA         = (110, 110, 110)
PRETO         = (30,  30,  30)
VERMELHO      = (192, 57,  43)
LARANJA       = (211, 84,  0)
BRANCO        = (255, 255, 255)


def _limpar(texto):
    if not texto:
        return ""
    return (str(texto)
        .replace("—", "-").replace("–", "-")
        .replace("‘", "'").replace("’", "'")
        .replace("“", '"').replace("”", '"')
        .encode("latin-1", errors="replace").decode("latin-1"))


class PDF(FPDF):
    def header(self):
        # Faixa verde escuro no topo
        self.set_fill_color(*VERDE_ESCURO)
        self.rect(0, 0, 210, 22, style="F")

        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*BRANCO)
        self.set_y(5)
        self.cell(0, 8, "Dashboard Zendesk  |  Exemplo",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        self.set_font("Helvetica", "", 8)
        self.set_text_color(210, 235, 218)
        agora = datetime.now().strftime("%d/%m/%Y  %H:%M")
        self.cell(0, 5, f"Gerado em {agora}",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        self.set_y(26)
        self.set_text_color(*PRETO)

    def footer(self):
        self.set_y(-12)
        self.set_fill_color(*VERDE_ESCURO)
        self.rect(0, self.get_y(), 210, 12, style="F")
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*BRANCO)
        self.cell(0, 10, f"Pagina {self.page_no()}  |  Escritório Contábil Exemplo", align="C")

    def titulo_secao(self, texto):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*VERDE_ESCURO)
        self.set_fill_color(*VERDE_CLARO)
        # Faixa lateral verde escuro
        self.set_draw_color(*VERDE_ESCURO)
        y = self.get_y()
        self.rect(10, y, 3, 7, style="F")
        self.set_x(15)
        self.cell(0, 7, _limpar(texto),
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=False)
        # Linha separadora
        self.set_draw_color(*VERDE_CLARO)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)

    def linha_dado(self, label, valor, cor_valor=None):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*CINZA)
        self.cell(65, 6, _limpar(label))
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*(cor_valor if cor_valor else PRETO))
        self.cell(0, 6, _limpar(str(valor)),
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def barra_horizontal(self, label, valor, maximo, largura_max=95):
        proporcao = (valor / maximo) if maximo > 0 else 0
        largura_barra = max(1, int(proporcao * largura_max))

        self.set_font("Helvetica", "", 9)
        self.set_text_color(*PRETO)
        self.cell(52, 6, _limpar(label)[:30])

        # Fundo da barra
        self.set_fill_color(*VERDE_CLARO)
        self.rect(self.get_x(), self.get_y() + 1.5, largura_max, 3.5, style="F")
        # Barra preenchida
        self.set_fill_color(*VERDE_BARRA)
        self.rect(self.get_x(), self.get_y() + 1.5, largura_barra, 3.5, style="F")

        self.set_x(self.get_x() + largura_max + 3)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*VERDE_ESCURO)
        self.cell(12, 6, str(valor),
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def calcular_tempo_aberto(timestamp_str):
    try:
        ts = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        delta = datetime.now() - ts
        horas = int(delta.total_seconds() // 3600)
        minutos = int((delta.total_seconds() % 3600) // 60)
        return f"{horas}h{minutos:02d}min" if horas > 0 else f"{minutos}min"
    except Exception:
        return "?"


def gerar_relatorio(caminho_saida=None):
    if caminho_saida is None:
        hoje_str = date.today().strftime("%Y-%m-%d")
        caminho_saida = os.path.join("data", f"relatorio_zendesk_{hoje_str}.pdf")

    m = calcular_metricas()
    if "erro" in m:
        print("Erro: sem dados no banco. Execute a coleta primeiro.")
        sys.exit(1)

    tickets_atrasados = buscar_tickets_abertos_atrasados(horas=2)
    hoje = date.today().strftime("%d/%m/%Y")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # --- Resumo ---
    pdf.titulo_secao("Resumo do dia - " + hoje)
    pdf.linha_dado("Tickets hoje:", m.get("total_hoje", 0))
    pdf.linha_dado("Total acumulado:", m.get("total", 0))
    pdf.linha_dado("Pendentes (abertos):", m.get("pendentes_hoje", 0), cor_valor=LARANJA)
    pdf.ln(5)

    # --- Periodo ---
    pdf.titulo_secao("Distribuicao por periodo (hoje)")
    por_periodo = m.get("por_periodo", {})
    pdf.linha_dado("Manha (6h-11h):",  por_periodo.get("Manha", 0))
    pdf.linha_dado("Tarde (12h-17h):", por_periodo.get("Tarde", 0))
    pdf.linha_dado("Noite (18h-23h):", por_periodo.get("Noite", 0))
    pdf.ln(5)

    # --- Grafico por setor ---
    por_setor = m.get("por_setor", {})
    pdf.titulo_secao("Tickets por setor (hoje)")
    if por_setor:
        maximo = max(por_setor.values())
        for setor, qtd in por_setor.items():
            pdf.barra_horizontal(setor, qtd, maximo)
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "Sem movimentacao hoje",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # --- Top 5 por setor ---
    top_por_setor = m.get("top_por_setor", {})
    pdf.titulo_secao("Top 5 colaboradores por setor (hoje)")
    if top_por_setor:
        for setor in sorted(top_por_setor.keys()):
            ranking = top_por_setor[setor]
            if not ranking:
                continue
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*VERDE_ESCURO)
            pdf.set_fill_color(*VERDE_CLARO)
            pdf.cell(0, 6, "  " + _limpar(setor),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
            for i, (nome, qtd) in enumerate(ranking.items(), 1):
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(*PRETO)
                pdf.cell(10, 5, f"  {i}.")
                pdf.cell(80, 5, _limpar(nome)[:40])
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(*VERDE_ESCURO)
                pdf.cell(0, 5, str(qtd),
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "Sem dados por setor hoje",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(5)

    # --- Top colaboradores ---
    top_colab = m.get("top_colaboradores", {})
    pdf.titulo_secao("Top colaboradores hoje")
    if top_colab:
        maximo_c = max(top_colab.values())
        for nome, qtd in list(top_colab.items())[:10]:
            pdf.barra_horizontal(nome, qtd, maximo_c)
    pdf.ln(5)

    # --- Top clientes ---
    top_clientes = m.get("top_clientes", {})
    pdf.titulo_secao("Top clientes hoje")
    if top_clientes:
        for i, (nome, qtd) in enumerate(list(top_clientes.items())[:10], 1):
            fill = i % 2 == 0
            pdf.set_fill_color(*VERDE_LINHA)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*PRETO)
            pdf.cell(8,  6, f"{i}.")
            pdf.cell(130, 6, _limpar(nome)[:60], fill=fill)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*VERDE_ESCURO)
            pdf.cell(0, 6, str(qtd),
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=fill)
    pdf.ln(5)

    # --- Tickets abertos mais de 2h (lista COMPLETA, nova pagina) ---
    pdf.add_page()
    total_atrasados = len(tickets_atrasados)
    pdf.titulo_secao(f"Tickets com mais de 2h em aberto - {total_atrasados} ticket(s)")

    if total_atrasados == 0:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*VERDE_ESCURO)
        pdf.cell(0, 6, "Nenhum ticket em atraso.",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    else:
        def _cabecalho_tabela():
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(*VERDE_ESCURO)
            pdf.set_text_color(*BRANCO)
            pdf.cell(18, 7, "Ticket",       border=0, fill=True)
            pdf.cell(50, 7, "Colaborador",  border=0, fill=True)
            pdf.cell(28, 7, "Setor",        border=0, fill=True)
            pdf.cell(62, 7, "Cliente",      border=0, fill=True)
            pdf.cell(30, 7, "Tempo aberto", border=0, fill=True,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        _cabecalho_tabela()

        for idx, row in enumerate(tickets_atrasados):
            numero, colab, setor, cliente, ts = row
            tempo = calcular_tempo_aberto(ts)

            if pdf.get_y() > 265:
                pdf.add_page()
                _cabecalho_tabela()

            fill = idx % 2 == 0
            pdf.set_fill_color(*(VERDE_LINHA if fill else BRANCO))
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*PRETO)
            pdf.cell(18, 6, _limpar(f"#{numero}"),       fill=fill)
            pdf.cell(50, 6, _limpar(colab or "")[:28],   fill=fill)
            pdf.cell(28, 6, _limpar(setor or "")[:15],   fill=fill)
            pdf.cell(62, 6, _limpar(cliente or "")[:35], fill=fill)

            try:
                horas_ab = (datetime.now() - datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")).total_seconds() / 3600
            except Exception:
                horas_ab = 0
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*(VERMELHO if horas_ab >= 4 else LARANJA))
            pdf.cell(30, 6, tempo, fill=fill,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(caminho_saida)
    print(f"\nPDF gerado: {caminho_saida}")
    return caminho_saida


if __name__ == "__main__":
    path = gerar_relatorio()
    try:
        import subprocess
        subprocess.Popen(["start", path], shell=True)
    except Exception:
        pass
