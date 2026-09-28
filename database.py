import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "tickets.db")

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def criar_banco():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE,
            numero TEXT,
            colaborador TEXT,
            setor TEXT,
            cliente TEXT,
            solicitante TEXT,
            status TEXT,
            prioridade TEXT,
            descricao TEXT,
            timestamp TEXT,
            hora INTEGER,
            periodo TEXT,
            data TEXT,
            alerta_enviado INTEGER DEFAULT 0,
            ts_slack TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Banco de dados criado em", DB_PATH)

def salvar_ticket(ticket: dict) -> bool:
    """Salva ticket no banco. Retorna True se inseriu, False se era duplicado."""
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO tickets (
                ticket_id, numero, colaborador, setor, cliente,
                solicitante, status, prioridade, descricao,
                timestamp, hora, periodo, data, ts_slack
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticket["ticket_id"], ticket["numero"], ticket["colaborador"],
            ticket["setor"], ticket["cliente"], ticket["solicitante"],
            ticket["status"], ticket["prioridade"], ticket["descricao"],
            ticket["timestamp"], ticket["hora"], ticket["periodo"],
            ticket["data"], ticket["ts_slack"]
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # duplicado, ignora
    finally:
        conn.close()

def buscar_todos():
    conn = get_conn()
    import pandas as pd
    df = pd.read_sql_query("SELECT * FROM tickets ORDER BY timestamp DESC", conn)
    conn.close()
    return df

def buscar_tickets_sem_alerta(horas_limite: int):
    """Retorna tickets abertos há mais de X horas sem alerta enviado."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ticket_id, numero, colaborador, cliente, timestamp
        FROM tickets
        WHERE status = 'aberto'
        AND alerta_enviado = 0
        AND datetime(timestamp) <= datetime('now', ?, 'localtime')
    """, (f"-{horas_limite} hours",))
    rows = cursor.fetchall()
    conn.close()
    return rows

def marcar_alerta_enviado(ticket_id: str):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET alerta_enviado = 1 WHERE ticket_id = ?", (ticket_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    criar_banco()

def buscar_tickets_abertos_atrasados(horas=2):
    """Retorna TODOS os tickets abertos ha mais de X horas (sem filtro de alerta)."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT numero, colaborador, setor, cliente, timestamp
        FROM tickets
        WHERE status = 'aberto'
        AND datetime(timestamp) <= datetime('now', ?, 'localtime')
        ORDER BY timestamp ASC
    """, (f"-{horas} hours",))
    rows = cursor.fetchall()
    conn.close()
    return rows
