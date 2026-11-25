import os, re, secrets, time, math, sys, json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_

# Ресурсы Flask находятся рядом с исходниками или внутри PyInstaller-сборки.
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")
# База хранится в профиле пользователя Windows и не теряется при перезапуске EXE.
DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "TverGuide")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "tver_excursions.db").replace("\\", "/")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DB_PATH
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    excursion_id = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "excursion_id"),)

EXCURSIONS = [
 {"id":1,"title":"Императорский маршрут: сердце Твери","place":"Императорский путевой дворец","date":"Ежедневно","time":"10:00","duration":"1 ч 30 мин","price":900,"category":"История","emoji":"🏛️","desc":"Знакомство с историей Путевого дворца, его архитектурой и визитами российских императоров."},
 {"id":2,"title":"Прогулка по набережной Волги","place":"Набережная Степана Разина","date":"Ежедневно","time":"11:30","duration":"1 ч","price":650,"category":"Прогулки","emoji":"🌊","desc":"Живописная прогулка вдоль Волги с рассказами о старой застройке и городских легендах."},
 {"id":3,"title":"Тверь купеческая","place":"Улица Трёхсвятская","date":"Пятница — воскресенье","time":"12:00","duration":"2 ч","price":800,"category":"История","emoji":"🏘️","desc":"Купеческие особняки, торговые ряды и истории предпринимателей старой Твери."},
 {"id":4,"title":"Морозовский городок: город в городе","place":"Морозовский городок","date":"Суббота","time":"13:00","duration":"1 ч 45 мин","price":750,"category":"Архитектура","emoji":"🧱","desc":"Архитектура рабочего посёлка, его необычные здания и история текстильной мануфактуры."},
 {"id":5,"title":"Мосты и панорамы Твери","place":"Старый Волжский мост","date":"Ежедневно","time":"16:00","duration":"1 ч 15 мин","price":600,"category":"Прогулки","emoji":"🌉","desc":"Городские виды, история мостов и лучшие точки для знакомства с панорамой Волги."},
 {"id":6,"title":"Тверь литературная","place":"Памятник А. С. Пушкину","date":"Воскресенье","time":"10:30","duration":"1 ч 30 мин","price":700,"category":"Культура","emoji":"📚","desc":"Литературные места города и истории о писателях, чья жизнь была связана с Тверским краем."},
 {"id":7,"title":"Секреты Тверского кремля","place":"Городской сад","date":"Суббота и воскресенье","time":"14:00","duration":"1 ч 30 мин","price":850,"category":"История","emoji":"🗝️","desc":"Где находился древний кремль, как менялся центр города и что скрывают старые улицы."},
 {"id":8,"title":"Архитектура трёх эпох","place":"Площадь Михаила Тверского","date":"Ежедневно","time":"15:00","duration":"2 ч","price":950,"category":"Архитектура","emoji":"🏙️","desc":"От регулярной планировки XVIII века до конструктивизма и современной городской среды."},
 {"id":9,"title":"Вечерняя Тверь в огнях","place":"Набережная Афанасия Никитина","date":"Пятница — воскресенье","time":"19:00","duration":"1 ч 20 мин","price":700,"category":"Прогулки","emoji":"🌆","desc":"Неспешный вечерний маршрут с красивыми видами на Волгу и подсвеченные мосты."},
 {"id":10,"title":"По следам Афанасия Никитина","place":"Памятник Афанасию Никитину","date":"Ежедневно","time":"12:30","duration":"1 ч 30 мин","price":800,"category":"Культура","emoji":"🧭","desc":"История знаменитого тверского путешественника и его эпохи."},
 {"id":11,"title":"Деревянное кружево старого города","place":"Улица Андрея Дементьева","date":"Суббота","time":"11:00","duration":"1 ч 40 мин","price":750,"category":"Архитектура","emoji":"🏡","desc":"Рассматриваем детали деревянных домов, резные наличники и тихие исторические улицы."},
 {"id":12,"title":"Городской сад и его истории","place":"Городской сад","date":"Ежедневно","time":"17:00","duration":"1 ч","price":500,"category":"Прогулки","emoji":"🌳","desc":"Зелёный центр Твери, памятники, старые аллеи и истории городского отдыха."},
 {"id":13,"title":"Тверь православная","place":"Спасо-Преображенский собор","date":"Воскресенье","time":"09:30","duration":"1 ч 30 мин","price":700,"category":"Культура","emoji":"⛪","desc":"Знакомство с историей храмов и духовным наследием города. Внешний осмотр объектов."},
 {"id":14,"title":"Необычные истории Твери","place":"Площадь Ленина","date":"Пятница","time":"18:00","duration":"1 ч 30 мин","price":650,"category":"Легенды","emoji":"🔎","desc":"Городские байки, неожиданные факты и малоизвестные страницы тверской истории."},
 {"id":15,"title":"Большая обзорная экскурсия","place":"Площадь Михаила Тверского","date":"Ежедневно","time":"10:00 и 15:00","duration":"2 ч 30 мин","price":1200,"category":"Обзорные","emoji":"🗺️","desc":"Главные достопримечательности Твери за одну прогулку: площади, набережные, мосты и памятники."},
 {"id":16,"title":"Закат над Волгой","place":"Набережная Афанасия Никитина","date":"Ежедневно","time":"20:00","duration":"1 ч","price":550,"category":"Прогулки","emoji":"🌅","desc":"Короткая прогулка в красивое время суток с рассказом о Волге и жизни города."}
]

def get_excursion(eid):
    return next((e for e in EXCURSIONS if e["id"] == eid), None)

def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]

app.jinja_env.globals["csrf_token"] = csrf_token

@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
        if not token or not secrets.compare_digest(token, session.get("_csrf", "")):
            abort(400, description="CSRF token missing or invalid")

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    response.headers["Cache-Control"] = "no-store" if request.path.startswith(("/admin", "/favorites", "/login", "/register")) else "public, max-age=60"
    return response

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Для доступа к этой странице войдите в аккаунт.", "warning")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = db.session.get(User, session.get("user_id")) if session.get("user_id") else None
        if not user or user.role != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapped

def valid_email(email):
    return bool(re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+", email or ""))

def valid_password(password):
    return (len(password or "") >= 10 and re.search(r"[A-ZА-Я]", password) and
            re.search(r"[a-zа-я]", password) and re.search(r"\d", password) and
            re.search(r"[^A-Za-zА-Яа-я0-9]", password))

# Lightweight in-memory throttling: per IP, shared by login attempts during this process.
LOGIN_ATTEMPTS = {}
def too_many_attempts(ip):
    now = time.time()
    attempts = [t for t in LOGIN_ATTEMPTS.get(ip, []) if now - t < 300]
    LOGIN_ATTEMPTS[ip] = attempts
    return len(attempts) >= 5

@app.context_processor
def inject_user():
    user = db.session.get(User, session.get("user_id")) if session.get("user_id") else None
    return {"current_user": user}

@app.route("/")
def index():
    return render_template("index.html", excursions=EXCURSIONS)

@app.route("/excursion/<int:excursion_id>")
def excursion_detail(excursion_id):
    item = get_excursion(excursion_id)
    if not item: abort(404)
    return render_template("detail.html", item=item)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        captcha = request.form.get("captcha", "").strip()
        expected = str(session.get("captcha_answer", ""))
        if not valid_email(email):
            flash("Введите корректный адрес электронной почты.", "error")
        elif not valid_password(password):
            flash("Пароль должен содержать минимум 10 символов, заглавную и строчную буквы, цифру и спецсимвол.", "error")
        elif captcha != expected:
            flash("Неверный ответ CAPTCHA. Попробуйте ещё раз.", "error")
        elif User.query.filter_by(email=email).first():
            flash("Аккаунт с такой почтой уже существует.", "error")
        else:
            user = User(email=email, password_hash=generate_password_hash(password))
            db.session.add(user); db.session.commit()
            session.clear()
            session["user_id"] = user.id
            flash("Регистрация прошла успешно!", "success")
            return redirect(url_for("index"))
    a, b = secrets.randbelow(8) + 2, secrets.randbelow(8) + 1
    session["captcha_answer"] = a + b
    return render_template("register.html", captcha_question=f"{a} + {b} = ?")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip = request.remote_addr or "unknown"
        if too_many_attempts(ip):
            abort(429, description="Слишком много попыток входа. Повторите через пять минут.")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            LOGIN_ATTEMPTS.pop(ip, None)
            session.clear()
            session["user_id"] = user.id
            flash("Вы успешно вошли в систему.", "success")
            target = request.args.get("next", "")
            return redirect(target if target.startswith("/") and not target.startswith("//") else url_for("index"))
        LOGIN_ATTEMPTS.setdefault(ip, []).append(time.time())
        flash("Неверная почта или пароль.", "error")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("Вы вышли из аккаунта.", "success")
    return redirect(url_for("index"))

@app.route("/favorites")
@login_required
def favorites():
    ids = {f.excursion_id for f in Favorite.query.filter_by(user_id=session["user_id"]).all()}
    items = [e for e in EXCURSIONS if e["id"] in ids]
    return render_template("favorites.html", excursions=items)

@app.route("/favorite/<int:excursion_id>", methods=["POST"])
@login_required
def toggle_favorite(excursion_id):
    if not get_excursion(excursion_id): abort(404)
    existing = Favorite.query.filter_by(user_id=session["user_id"], excursion_id=excursion_id).first()
    if existing:
        db.session.delete(existing); flash("Экскурсия удалена из избранного.", "success")
    else:
        db.session.add(Favorite(user_id=session["user_id"], excursion_id=excursion_id)); flash("Экскурсия добавлена в избранное.", "success")
    db.session.commit()
    return redirect(request.form.get("next") or url_for("favorites"))

@app.route("/search", methods=["GET", "POST"])
def search():
    query = (request.values.get("q") or "").strip()
    results = []
    if query:
        terms = query.casefold()
        results = [e for e in EXCURSIONS if terms in (e["title"] + " " + e["place"] + " " + e["desc"] + " " + e["category"]).casefold()]
    return render_template("search.html", query=query, results=results)

@app.route("/admin")
@login_required
@admin_required
def admin():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin.html", users=users)

@app.route("/admin/user/<int:user_id>/role", methods=["POST"])
@login_required
@admin_required
def change_role(user_id):
    user = db.session.get(User, user_id)
    if not user: abort(404)
    role = request.form.get("role")
    if role not in ("user", "admin"): abort(400)
    if user.id == session["user_id"] and role != "admin":
        flash("Нельзя снять роль администратора с собственной учётной записи.", "error")
    else:
        user.role = role; db.session.commit(); flash("Роль пользователя обновлена.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user: abort(404)
    if user.id == session["user_id"]:
        flash("Нельзя удалить собственную учётную запись.", "error")
    else:
        Favorite.query.filter_by(user_id=user.id).delete()
        db.session.delete(user); db.session.commit(); flash("Пользователь удалён.", "success")
    return redirect(url_for("admin"))

@app.route("/api/excursions")
def api_excursions():
    return jsonify(EXCURSIONS)

@app.errorhandler(400)
def bad_request(error):
    return render_template("error.html", code=400, message="Некорректный запрос или ошибка CSRF-защиты."), 400

@app.errorhandler(403)
def forbidden(error):
    return render_template("error.html", code=403, message="У вас нет прав для просмотра этой страницы."), 403

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404, message="Такой страницы не существует."), 404

@app.errorhandler(429)
def rate_limited(error):
    return render_template("error.html", code=429, message="Слишком много запросов. Попробуйте позже."), 429

def load_secrets():
    """Безопасно загружает секреты из файла secrets.json, если он существует"""
    secrets_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'secrets.json')
    if os.path.exists(secrets_file):
        try:
            with open(secrets_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def initialize():
    with app.app_context():
        db.create_all()
        
        # Загружаем данные из secrets.json
        secrets_data = load_secrets()
        
        # Ищем пароль: 1. в переменных среды, 2. в secrets.json, 3. запасной вариант
        admin_email = os.environ.get(
            "ADMIN_EMAIL", 
            secrets_data.get("ADMIN_EMAIL", "admin@tver-tour.local")
        ).lower()
        
        admin_password = os.environ.get(
            "ADMIN_PASSWORD", 
            secrets_data.get("ADMIN_PASSWORD", "Admin123!Change")
        )
        
        if not User.query.filter_by(email=admin_email).first():
            db.session.add(User(
                email=admin_email, 
                password_hash=generate_password_hash(admin_password), 
                role="admin"
            ))
            db.session.commit()
            print(f"✅ Админ создан: {admin_email} (пароль взят из secrets.json или переменных окружения)")
        else:
            print(f"ℹ️ Админ уже существует: {admin_email}")

initialize()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=False)