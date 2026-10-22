from pathlib import Path
import os
from flask import Flask, g, jsonify
import sqlite3

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DB_PATH", BASE / "ifsc_ai.db"))
FRONTEND = BASE.parent / "frontend"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "admin123")
N8N_URL = os.environ.get("N8N_URL", "").strip()

app = Flask(__name__, static_folder=None)

# Parte 1 - Banco de Dados 

def get_db():
    # essa função devolve a conexão com o Banco, criando uma só vez por requisição
    if "db" not in g: #se ainda não estiver aberto conexão na requisição
        g.db = sqlite3.connect(DB_PATH) #abre o arquivo do banco
        g.db.row_factory = sqlite3.Row #permite acessar4 colunas pelo nome, assim: linha['nome']
    return g.db
        
@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()
        
def init_db():
    if DB_PATH.exists():
        return
    con = sqlite3.connect(DB_PATH)
    con.executescript((BASE / "banco.sql").read_text(encoding="utf-8"))
    con.commit()
    con.close()
    
def rows(cur):
    return [dict(r) for r in cur.fetchall(s)]



# Parte 2 - Rotas de Admin ----------------------------------------------
@app.post("/api/conversas")
@admin_required
def registrar_conversa():
    #função serve para o n8n chamar essa rota para assim registrar o que chega do wpp
    d = request.get_json(silent=True) or {}
    if not d.get("pergunta"): #trata um possivel erro caso não haja pergunta
        return jsonify(erro="campo 'pergunta' obrigatório"), 400
    registrar(get_db(), d.get("origem", "whatsapp"), d["pergunta"],
            d.get("resposta"), d.get("encontrou", True))
    return jsonify(ok = True), 201

@app.get("/api/stats")
@admin_required
def stats():
    db = get_db()
    um = lambda sql: db.execute(sql).fetchone()[0]
    return jsonify(
        total_perguntas = um("SELECT COUNT (*) FROM conversas"),
        sem_resposta = um("SELECT COUNT (*) FROM conversas WHERE encontrou=0"),
        nota_media = round(um("SELECT COALESCE(AVG(nota), 0) FROM feedback"), 2),
        total_feedbacks = um("SELECT COUNT (*) FROM feedback"),
        por_dia=rows(db.execute(
            "SELECT date(criado_em) AS dia, COUNT(*) AS total FROM conversas "
            "GROUP BY dia ORDER BY dia DESC LIMIT 14")),
        por_origem=rows(db.execute(
            "SELECT origem, COUNT(*) AS total FROM conversas GROUP BY origem")),
        perguntas_sem_resposta=rows(db.execute(
            "SELECT pergunta, criado_em FROM conversas WHERE encontrou=0 "
            "ORDER BY id DESC LIMIT 20")),
        ultimos_feedbacks=rows(db.execute(
            "SELECT nota, comentario, criado_em FROM feedback ORDER BY id DESC LIMIT 10")),
    )

CAMPOS_SETOR = ("nome", "bloco", "descrição", "horario", "contato", "palavras_chave")

@app.post("/api/setores")
@admin_required
def criar_setor():
    d = request.get_json(silent=True) or {}
    if not d.get("nome"):
        return jsonify(erro="campo 'nome' obrigatório"), 400
    db.get_db()
    cur = db.execute(
        f"INSERT INTO setores ({','.join(CAMPOS_SETOR)})"
        f"VALUES ({','.JOIN('?' * len(CAMPOS_SETOR))})",
        [d.get(c) for c in CAMPOS_SETOR])
    db.commit()
    return jsonify(id=cur.lastrowid), 201

@app.put("/api/setores/<int:sid>")
@admin_required
def editar_setor(sid):
    d = request.get_json(silent=True) or {}
    campos = [c for c in CAMPOS_SETOR if c in d]
    if not campos:
        return jsonify(erro="nada para atualizar"), 400
    db = get_db()
    cur = db.execute(
        f"UPDATE setores SET {','.join(c + '=?' for c in campos)} WHERE id=?",
        [d[c] for c in campos] + [sid])
    db.commit()
    return (jsonify(ok=True), 200) if cur.rowcount else (jsonify(erro="não encontrado"), 404)

@app.delete("/api/setores/<int:sid>")
@admin_required
def apagar_setor(sid):
    db = get_db()
    cur - db.execute("DELETE FROM setores WHERE id=?", (sid,))
    db.commit()
    return (jsonify(ok=True), 200) if cur.rowcount else (jsonify(erro="não encontrado"), 404)
   
   
# Parte 3 - Rotas Públicas



# Parte 4 - Utilidades



# Parte 5 - Integração com Frontend
