"""DoaFácil — MVP acadêmico em Flask + SQLite.

Iniciar: pip install -r requirements.txt && python app.py
"""
from __future__ import annotations

import os
import secrets
import sqlite3
import uuid
from functools import wraps
from io import BytesIO
from pathlib import Path

import click
from flask import (
    Flask, abort, flash, g, redirect, render_template,
    request, session, url_for,
)
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "doafacil.sqlite3"
CATEGORIES = ["Roupas", "Livros", "Brinquedos", "Material escolar", "Casa", "Eletrônicos", "Outros"]
CONDITIONS = ["Novo", "Bom estado", "Usado"]
STATES = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=6 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("HTTPS_ONLY", "0") == "1",
    UPLOAD_FOLDER=str(BASE_DIR / "static" / "uploads"),
)


# Fotografias reais de demonstração (Unsplash). Os anúncios fictícios antigos
# ainda guardam caminhos SVG no SQLite; o filtro traduz sem apagar o banco.
DEMO_PHOTOS = {
    "img/mochila.svg": "https://images.unsplash.com/photo-1535982330050-f1c2fb79ff78?auto=format&fit=crop&w=1000&q=82",
    "img/livros.svg": "https://images.unsplash.com/photo-1692742593479-7b37552a4815?auto=format&fit=crop&w=1000&q=82",
    "img/urso.svg": "https://images.unsplash.com/photo-1765913186506-a4f1ca060ced?auto=format&fit=crop&w=1000&q=82",
    "img/luminaria.svg": "https://images.unsplash.com/photo-1678819483347-3faeb1e426c0?auto=format&fit=crop&w=1000&q=82",
    "img/casaco.svg": "https://images.unsplash.com/photo-1559436194-ec317a4bafeb?auto=format&fit=crop&w=1000&q=82",
    "img/cadernos.svg": "https://images.unsplash.com/photo-1531346618680-ab17d6dcd07c?auto=format&fit=crop&w=1000&q=82",
    "img/celular.svg": "https://images.unsplash.com/photo-1563030646-2957db71d197?auto=format&fit=crop&w=1000&q=82",
    "img/hero-doacao.svg": "https://images.unsplash.com/photo-1593113646773-028c64a8f1b8?auto=format&fit=crop&w=1000&q=82",
}


@app.template_filter("photo_url")
def photo_url(path):
    """Resolve fotos do usuário e fotografias dos anúncios de exemplo."""
    if not path:
        return ""
    if path in DEMO_PHOTOS:
        return DEMO_PHOTOS[path]
    if path.startswith("https://images.unsplash.com/"):
        return path
    return url_for("static", filename=path)


def db():
    if "db" not in g:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(DB_PATH, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def one(query, params=()):
    return db().execute(query, params).fetchone()


def all_rows(query, params=()):
    return db().execute(query, params).fetchall()


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


@app.before_request
def load_user_and_check_csrf():
    user_id = session.get("user_id")
    g.user = one("SELECT * FROM users WHERE id=? AND is_active=1", (user_id,)) if user_id else None
    if user_id and g.user is None:
        session.clear()
    if request.method == "POST":
        token = request.form.get("csrf_token", "")
        if not secrets.compare_digest(token, session.get("csrf", "!")):
            abort(400, description="Formulário expirado. Atualize a página e tente novamente.")


@app.context_processor
def inject_globals():
    return {
        "current_user": g.get("user"),
        "csrf_token": csrf_token,
        "categories": CATEGORIES,
        "states": STATES,
        "conditions": CONDITIONS,
    }


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Entre na sua conta para continuar.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def owner_only(donation_id):
    donation = one("SELECT * FROM donations WHERE id=?", (donation_id,))
    if not donation:
        abort(404)
    if donation["owner_id"] != g.user["id"]:
        abort(403)
    return donation


def get_photo(form_file):
    """Recebe foto JPG/PNG/WEBP, valida pixels e salva versão JPG redimensionada."""
    if not form_file or not form_file.filename:
        return None
    try:
        data = form_file.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024:
            raise ValueError("A imagem deve ter até 5 MB.")
        original = Image.open(BytesIO(data))
        if original.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError("Envie uma imagem JPG, PNG ou WEBP.")
        if original.width * original.height > 20_000_000:
            raise ValueError("A imagem tem resolução muito alta.")
        original.load()
        img = ImageOps.exif_transpose(original)
        img.thumbnail((1400, 1400))
        if img.mode in ("RGBA", "LA") or "transparency" in img.info:
            bg = Image.new("RGB", img.size, "white")
            bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").getchannel("A"))
            img = bg
        else:
            img = img.convert("RGB")
        filename = f"{uuid.uuid4().hex}.jpg"
        upload_dir = Path(app.config["UPLOAD_FOLDER"])
        upload_dir.mkdir(parents=True, exist_ok=True)
        img.save(upload_dir / filename, format="JPEG", quality=84, optimize=True)
        return f"uploads/{filename}"
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValueError(str(exc) if isinstance(exc, ValueError) else "Não foi possível ler esta imagem.") from exc


def donation_input():
    values = {
        "title": request.form.get("title", "").strip(),
        "description": request.form.get("description", "").strip(),
        "category": request.form.get("category", "").strip(),
        "item_condition": request.form.get("item_condition", "").strip(),
        "city": request.form.get("city", "").strip(),
        "state": request.form.get("state", "").strip().upper(),
    }
    if not 3 <= len(values["title"]) <= 90:
        raise ValueError("O nome do objeto deve ter de 3 a 90 caracteres.")
    if not 10 <= len(values["description"]) <= 700:
        raise ValueError("A descrição deve ter de 10 a 700 caracteres.")
    if values["category"] not in CATEGORIES or values["item_condition"] not in CONDITIONS:
        raise ValueError("Selecione a categoria e o estado de conservação.")
    if not 2 <= len(values["city"]) <= 80 or values["state"] not in STATES:
        raise ValueError("Informe cidade e estado válidos.")
    return values


@app.route("/")
def home():
    latest = all_rows("""
        SELECT d.*, u.name AS owner_name FROM donations d
        JOIN users u ON u.id=d.owner_id
        WHERE d.status='disponivel' AND d.is_visible=1 AND u.is_active=1
        ORDER BY d.created_at DESC, d.id DESC LIMIT 6
    """)
    counts = {
        "available": one("SELECT COUNT(*) AS n FROM donations WHERE status='disponivel' AND is_visible=1")["n"],
        "delivered": one("SELECT COUNT(*) AS n FROM donations WHERE status='doado'")["n"],
        "users": one("SELECT COUNT(*) AS n FROM users WHERE is_active=1 AND role='user'")["n"],
    }
    return render_template("home.html", latest=latest, counts=counts)


@app.route("/doacoes")
def explore():
    q = request.args.get("q", "").strip()[:90]
    cat = request.args.get("categoria", "").strip()
    city = request.args.get("cidade", "").strip()[:80]
    filters = ["d.status='disponivel'", "d.is_visible=1", "u.is_active=1"]
    values = []
    if q:
        filters.append("(d.title LIKE ? OR d.description LIKE ?)")
        values.extend([f"%{q}%", f"%{q}%"])
    if cat in CATEGORIES:
        filters.append("d.category=?")
        values.append(cat)
    else:
        cat = ""
    if city:
        filters.append("d.city LIKE ?")
        values.append(f"%{city}%")
    items = all_rows(f"""
        SELECT d.*, u.name AS owner_name FROM donations d
        JOIN users u ON u.id=d.owner_id
        WHERE {' AND '.join(filters)} ORDER BY d.created_at DESC, d.id DESC LIMIT 120
    """, values)
    return render_template("explore.html", items=items, q=q, selected_category=cat, selected_city=city)


@app.route("/doacoes/<int:donation_id>")
def detail(donation_id):
    item = one("""
        SELECT d.*, u.name AS owner_name, u.city AS owner_city, u.is_active AS owner_active
        FROM donations d JOIN users u ON u.id=d.owner_id WHERE d.id=?
    """, (donation_id,))
    if not item:
        abort(404)
    privileged = g.user and (g.user["id"] == item["owner_id"] or g.user["role"] == "admin")
    if (not item["is_visible"] or not item["owner_active"]) and not privileged:
        abort(404)
    my_request = None
    if g.user:
        my_request = one("SELECT * FROM requests WHERE donation_id=? AND requester_id=?", (donation_id, g.user["id"]))
    return render_template("detail.html", item=item, my_request=my_request)


@app.route("/cadastrar", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        city = request.form.get("city", "").strip()
        password = request.form.get("password", "")
        if not 2 <= len(name) <= 80 or not 2 <= len(city) <= 80 or not 5 <= len(email) <= 150 or "@" not in email:
            flash("Preencha nome, cidade e um e-mail válido.", "error")
        elif len(password) < 8 or len(password) > 128:
            flash("A senha deve ter de 8 a 128 caracteres.", "error")
        else:
            try:
                cur = db().execute("INSERT INTO users (name,email,password_hash,city) VALUES (?,?,?,?)", (name, email, generate_password_hash(password), city))
                db().commit()
                session.clear()
                session["user_id"] = cur.lastrowid
                flash("Conta criada com sucesso! Bem-vindo(a) ao DoaFácil.", "success")
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                flash("Já existe uma conta com este e-mail.", "error")
    return render_template("auth.html", mode="register")


@app.route("/entrar", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        u = one("SELECT * FROM users WHERE email=?", (email,))
        if u and u["is_active"] and check_password_hash(u["password_hash"], password):
            session.clear()
            session["user_id"] = u["id"]
            flash("Que bom ter você por aqui!", "success")
            return redirect(url_for("dashboard"))
        flash("E-mail ou senha incorretos, ou conta desativada.", "error")
    return render_template("auth.html", mode="login")


@app.post("/sair")
@login_required
def logout():
    session.clear()
    flash("Você saiu da sua conta.", "success")
    return redirect(url_for("home"))


@app.route("/doacoes/nova", methods=["GET", "POST"])
@login_required
def new_donation():
    if request.method == "POST":
        try:
            data = donation_input()
            image_path = get_photo(request.files.get("image"))
            db().execute("""
                INSERT INTO donations (owner_id,title,description,category,item_condition,city,state,image_path)
                VALUES (:owner_id,:title,:description,:category,:item_condition,:city,:state,:image_path)
            """, {**data, "owner_id": g.user["id"], "image_path": image_path})
            db().commit()
            flash("Doação publicada! Agora ela aparece para outras pessoas.", "success")
            return redirect(url_for("mine"))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("donation_form.html", item=None)


@app.route("/doacoes/<int:donation_id>/editar", methods=["GET", "POST"])
@login_required
def edit_donation(donation_id):
    item = owner_only(donation_id)
    if item["status"] != "disponivel":
        flash("Somente doações disponíveis podem ser editadas.", "warning")
        return redirect(url_for("mine"))
    if request.method == "POST":
        try:
            data = donation_input()
            uploaded = get_photo(request.files.get("image"))
            data["image_path"] = uploaded or item["image_path"]
            db().execute("""
                UPDATE donations SET title=:title, description=:description, category=:category,
                item_condition=:item_condition, city=:city, state=:state, image_path=:image_path
                WHERE id=:id AND status='disponivel'
            """, {**data, "id": donation_id})
            db().commit()
            flash("Anúncio atualizado com sucesso.", "success")
            return redirect(url_for("mine"))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("donation_form.html", item=item)


@app.post("/doacoes/<int:donation_id>/excluir")
@login_required
def delete_donation(donation_id):
    item = owner_only(donation_id)
    if item["status"] != "disponivel":
        flash("Não é possível excluir uma doação reservada ou concluída.", "error")
        return redirect(url_for("mine"))
    db().execute("DELETE FROM donations WHERE id=?", (donation_id,))
    db().commit()
    flash("Anúncio excluído.", "success")
    return redirect(url_for("mine"))


@app.post("/doacoes/<int:donation_id>/solicitar")
@login_required
def request_donation(donation_id):
    item = one("SELECT d.*,u.is_active AS owner_active FROM donations d JOIN users u ON u.id=d.owner_id WHERE d.id=?", (donation_id,))
    if not item or not item["is_visible"] or not item["owner_active"]:
        abort(404)
    if item["owner_id"] == g.user["id"]:
        flash("Você não pode solicitar seu próprio anúncio.", "error")
        return redirect(url_for("detail", donation_id=donation_id))
    try:
        # BEGIN IMMEDIATE evita duas alterações simultâneas incompatíveis no SQLite.
        db().execute("BEGIN IMMEDIATE")
        current = one("SELECT status FROM donations WHERE id=?", (donation_id,))
        if not current or current["status"] != "disponivel":
            db().rollback()
            flash("Esta doação não está mais disponível.", "warning")
            return redirect(url_for("explore"))
        existing = one("SELECT * FROM requests WHERE donation_id=? AND requester_id=?", (donation_id, g.user["id"]))
        if existing:
            if existing["status"] != "cancelada":
                db().rollback()
                flash("Você já enviou uma solicitação para este item.", "warning")
                return redirect(url_for("detail", donation_id=donation_id))
            db().execute("UPDATE requests SET status='pendente',updated_at=CURRENT_TIMESTAMP WHERE id=?", (existing["id"],))
        else:
            db().execute("INSERT INTO requests (donation_id,requester_id) VALUES (?,?)", (donation_id, g.user["id"]))
        db().commit()
        flash("Solicitação enviada! Acompanhe o andamento em Solicitações.", "success")
    except sqlite3.IntegrityError:
        db().rollback()
        flash("Não foi possível enviar esta solicitação.", "error")
    return redirect(url_for("requests_page"))


@app.route("/painel")
@login_required
def dashboard():
    uid = g.user["id"]
    counts = {
        "my_donations": one("SELECT COUNT(*) n FROM donations WHERE owner_id=?", (uid,))["n"],
        "my_pending": one("SELECT COUNT(*) n FROM requests WHERE requester_id=? AND status='pendente'", (uid,))["n"],
        "received_pending": one("SELECT COUNT(*) n FROM requests r JOIN donations d ON d.id=r.donation_id WHERE d.owner_id=? AND r.status='pendente'", (uid,))["n"],
        "my_completed": one("SELECT COUNT(*) n FROM donations WHERE owner_id=? AND status='doado'", (uid,))["n"],
    }
    recent = all_rows("SELECT * FROM donations WHERE owner_id=? ORDER BY created_at DESC,id DESC LIMIT 4", (uid,))
    return render_template("dashboard.html", counts=counts, recent=recent)


@app.route("/minhas-doacoes")
@login_required
def mine():
    items = all_rows("""
        SELECT d.*, (SELECT COUNT(*) FROM requests r WHERE r.donation_id=d.id AND r.status='pendente') AS pending_count
        FROM donations d WHERE d.owner_id=? ORDER BY d.created_at DESC,d.id DESC
    """, (g.user["id"],))
    return render_template("mine.html", items=items)


@app.route("/solicitacoes")
@login_required
def requests_page():
    uid = g.user["id"]
    received = all_rows("""
        SELECT r.*, d.title, d.image_path, d.city, d.state, d.owner_id, d.status AS donation_status,
               u.name AS requester_name, u.email AS requester_email
        FROM requests r JOIN donations d ON d.id=r.donation_id
        JOIN users u ON u.id=r.requester_id
        WHERE d.owner_id=? ORDER BY r.created_at DESC,r.id DESC
    """, (uid,))
    sent = all_rows("""
        SELECT r.*, d.title, d.image_path, d.city, d.state, d.status AS donation_status,
               u.name AS owner_name, u.email AS owner_email
        FROM requests r JOIN donations d ON d.id=r.donation_id
        JOIN users u ON u.id=d.owner_id
        WHERE r.requester_id=? ORDER BY r.created_at DESC,r.id DESC
    """, (uid,))
    return render_template("requests.html", received=received, sent=sent)


@app.post("/solicitacoes/<int:request_id>/aprovar")
@login_required
def approve_request(request_id):
    try:
        db().execute("BEGIN IMMEDIATE")
        req = one("""
            SELECT r.*, d.owner_id,d.status AS donation_status,d.is_visible
            FROM requests r JOIN donations d ON d.id=r.donation_id WHERE r.id=?
        """, (request_id,))
        if not req:
            db().rollback()
            abort(404)
        if req["owner_id"] != g.user["id"]:
            db().rollback()
            abort(403)
        if req["status"] != "pendente" or req["donation_status"] != "disponivel" or not req["is_visible"]:
            db().rollback()
            flash("Esta solicitação não pode mais ser aprovada.", "error")
            return redirect(url_for("requests_page"))
        db().execute("UPDATE requests SET status='aprovada',updated_at=CURRENT_TIMESTAMP WHERE id=?", (request_id,))
        db().execute("UPDATE requests SET status='recusada',updated_at=CURRENT_TIMESTAMP WHERE donation_id=? AND id!=? AND status='pendente'", (req["donation_id"], request_id))
        db().execute("UPDATE donations SET status='reservado' WHERE id=?", (req["donation_id"],))
        db().commit()
        flash("Solicitação aprovada! O e-mail de contato já aparece para os envolvidos.", "success")
    except sqlite3.IntegrityError:
        db().rollback()
        flash("Não foi possível aprovar a solicitação.", "error")
    return redirect(url_for("requests_page"))


@app.post("/solicitacoes/<int:request_id>/recusar")
@login_required
def reject_request(request_id):
    req = one("""
        SELECT r.*,d.owner_id FROM requests r JOIN donations d ON d.id=r.donation_id WHERE r.id=?
    """, (request_id,))
    if not req:
        abort(404)
    if req["owner_id"] != g.user["id"]:
        abort(403)
    if req["status"] != "pendente":
        flash("Solicitação já processada.", "warning")
    else:
        db().execute("UPDATE requests SET status='recusada',updated_at=CURRENT_TIMESTAMP WHERE id=?", (request_id,))
        db().commit()
        flash("Solicitação recusada.", "success")
    return redirect(url_for("requests_page"))


@app.post("/solicitacoes/<int:request_id>/cancelar")
@login_required
def cancel_request(request_id):
    req = one("SELECT * FROM requests WHERE id=?", (request_id,))
    if not req:
        abort(404)
    if req["requester_id"] != g.user["id"]:
        abort(403)
    if req["status"] == "pendente":
        db().execute("UPDATE requests SET status='cancelada',updated_at=CURRENT_TIMESTAMP WHERE id=?", (request_id,))
        db().commit()
        flash("Solicitação cancelada.", "success")
    else:
        flash("Somente solicitações pendentes podem ser canceladas.", "warning")
    return redirect(url_for("requests_page"))


@app.post("/doacoes/<int:donation_id>/concluir")
@login_required
def complete_donation(donation_id):
    item = owner_only(donation_id)
    if item["status"] != "reservado":
        flash("Para concluir uma doação, primeiro aprove uma solicitação.", "warning")
    else:
        db().execute("UPDATE donations SET status='doado' WHERE id=?", (donation_id,))
        db().execute("UPDATE requests SET status='concluida',updated_at=CURRENT_TIMESTAMP WHERE donation_id=? AND status='aprovada'", (donation_id,))
        db().commit()
        flash("Entrega confirmada! Obrigado por fazer a diferença.", "success")
    return redirect(url_for("mine"))


@app.route("/admin")
@admin_required
def admin():
    stats = {
        "users": one("SELECT COUNT(*) n FROM users")["n"],
        "donations": one("SELECT COUNT(*) n FROM donations")["n"],
        "pending": one("SELECT COUNT(*) n FROM requests WHERE status='pendente'")["n"],
        "completed": one("SELECT COUNT(*) n FROM donations WHERE status='doado'")["n"],
    }
    users = all_rows("SELECT * FROM users ORDER BY created_at DESC,id DESC LIMIT 100")
    items = all_rows("""
        SELECT d.*,u.name AS owner_name FROM donations d JOIN users u ON u.id=d.owner_id
        ORDER BY d.created_at DESC,d.id DESC LIMIT 100
    """)
    return render_template("admin.html", stats=stats, users=users, items=items)


@app.post("/admin/usuarios/<int:user_id>/alternar")
@admin_required
def admin_toggle_user(user_id):
    u = one("SELECT * FROM users WHERE id=?", (user_id,))
    if not u:
        abort(404)
    if user_id == g.user["id"] or u["role"] == "admin":
        abort(403)
    db().execute("UPDATE users SET is_active=1-is_active WHERE id=?", (user_id,))
    db().commit()
    flash("Situação do usuário atualizada.", "success")
    return redirect(url_for("admin") + "#usuarios")


@app.post("/admin/doacoes/<int:donation_id>/alternar")
@admin_required
def admin_toggle_donation(donation_id):
    if not one("SELECT id FROM donations WHERE id=?", (donation_id,)):
        abort(404)
    db().execute("UPDATE donations SET is_visible=1-is_visible WHERE id=?", (donation_id,))
    db().commit()
    flash("Visibilidade do anúncio atualizada.", "success")
    return redirect(url_for("admin") + "#anuncios")


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(413)
def error_page(error):
    messages = {400: "Solicitação inválida. Atualize a página e tente novamente.",
                403: "Você não tem autorização para acessar esta página.",
                404: "Não encontramos o que você está procurando.",
                413: "O arquivo enviado é muito grande. Use uma foto com até 5 MB."}
    return render_template("error.html", code=error.code, message=messages.get(error.code, "Algo deu errado.")), error.code


def seed_demo():
    """Perfis e itens fictícios somente para demonstração acadêmica local."""
    if os.environ.get("DEMO_DATA", "1") != "1":
        return
    if one("SELECT COUNT(*) AS n FROM users")["n"]:
        return
    demo_pass = generate_password_hash("Demo@123")
    demo_users = [
        ("Ana Oliveira", "ana@exemplo.com", demo_pass, "Belém", "user"),
        ("João Santos", "joao@exemplo.com", demo_pass, "Benevides", "user"),
        ("Administradora", "admin@doafacil.local", demo_pass, "Belém", "admin"),
    ]
    db().executemany("INSERT INTO users (name,email,password_hash,city,role) VALUES (?,?,?,?,?)", demo_users)
    demo_items = [
        (1, "Mochila escolar azul", "Mochila resistente em bom estado, com dois compartimentos e zíper funcionando.", "Material escolar", "Bom estado", "Belém", "PA", "img/mochila.svg"),
        (1, "Livros de literatura", "Coleção de livros de literatura juvenil, conservados e prontos para novos leitores.", "Livros", "Bom estado", "Belém", "PA", "img/livros.svg"),
        (2, "Ursinho de pelúcia", "Ursinho limpo e bem cuidado, ideal para presentear uma criança.", "Brinquedos", "Bom estado", "Benevides", "PA", "img/urso.svg"),
        (2, "Luminária de mesa", "Luminária de mesa funcionando normalmente, com iluminação adequada para estudos.", "Casa", "Usado", "Marituba", "PA", "img/luminaria.svg"),
        (1, "Casaco de moletom", "Casaco de moletom tamanho M, higienizado e em boas condições de uso.", "Roupas", "Bom estado", "Ananindeua", "PA", "img/casaco.svg"),
        (2, "Cadernos novos", "Três cadernos sem uso disponíveis para estudantes que precisam de material.", "Material escolar", "Novo", "Benevides", "PA", "img/cadernos.svg"),
    ]
    db().executemany("""
        INSERT INTO donations (owner_id,title,description,category,item_condition,city,state,image_path)
        VALUES (?,?,?,?,?,?,?,?)
    """, demo_items)
    db().commit()


def init_database():
    with app.app_context():
        db().executescript((BASE_DIR / "schema.sql").read_text(encoding="utf-8"))
        db().commit()
        seed_demo()


@app.cli.command("init-db")
def init_db_command():
    """Cria as tabelas necessárias, se não existirem."""
    init_database()
    click.echo("Banco inicializado.")


# A inicialização é idempotente e facilita executar com 'python app.py' ou 'flask run'.
init_database()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG") == "1")
