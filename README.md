# Demonstração — Dashboard de atendimento Zendesk e Slack

> Projeto de portfólio de **Victória Pedrosa**. **Demonstração** de dashboard de atendimento Zendesk e Slack — versão com dados fictícios (nomes, CNPJs, e-mails e IDs internos substituídos).

## Problema de negócio
A liderança não tinha visão diária do atendimento (tickets, menções, tempo de resposta).

## Antes x depois
| | Antes | Depois |
|---|---|---|
| Como é feito | Métricas levantadas manualmente no Zendesk. | Coletor lê o Zendesk, grava em banco, publica dashboard no Slack (Home e Canvas), gera PDF e alerta menções. |

## Ganho
- Métricas de atendimento atualizadas a cada 5 minutos no Slack.

## Tecnologias
Chart.js, HTML/JavaScript, Python, SQLite, Slack API, Zendesk API, pandas

## Arquivos
- `app_home.py`
- `canvas_updater.py`
- `collector.py`
- `config.py`
- `dashboard.py`
- `database.py`
- `diagnostico.bat`
- `gerar_dashboard.py`
- `gerar_pdf.bat`
- `gerar_pdf.py`
- `iniciar_silencioso.vbs`
- `instalar_dependencias.bat`
- `instalar_inicio_automatico.bat`
- `instalar_pacotes.bat`
- `main.py`
- `mencoes.bat`
- `mencoes.py`
- `mencoes_pdf.py`
- `mencoes_refresh.py`
- `metrics.py`
- `notificador.py`
- `parser.py`
- `reiniciar_bot.bat`
- `requirements.txt`
- `rodar.bat`
- `rodar_scheduler.bat`
- `rodar_socket.bat`
- `scheduler.py`
- `slack_mencoes.html`
- `socket_handler.py`
- `testar_scheduler.bat`

## Como rodar
1. `pip install -r requirements.txt`
2. Copie `.env.exemplo` para `.env` e preencha os caminhos.
3. Execute o script principal.

## Autora
Victória Pedrosa — Product Owner do Time de IA, automação de processos contábeis e fiscais.
