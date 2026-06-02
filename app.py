import json
import os
import re
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from sqlalchemy import inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from i18n import get_text
from models import Admin, User, Work, db

login_manager = LoginManager()


@login_manager.unauthorized_handler
def unauthorized():
    if request.endpoint and str(request.endpoint).startswith("admin"):
        return redirect(url_for("admin_login", next=request.url))
    flash(get_text("login_required", session.get("lang", "zh")), "error")
    return redirect(url_for("user_login", next=request.url))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        if user_id.startswith("admin-"):
            return db.session.get(Admin, int(user_id[6:]))
        if user_id.startswith("user-"):
            return db.session.get(User, int(user_id[5:]))
        return None

    with app.app_context():
        db.create_all()
        _migrate_schema()
        _ensure_admin(app)

    register_routes(app)
    return app


def _migrate_schema():
    """Add new columns to existing SQLite DB."""
    inspector = inspect(db.engine)
    if "works" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("works")}
    alters = []
    if "grade" not in existing:
        if "department" in existing:
            alters.append("ALTER TABLE works RENAME COLUMN department TO grade")
        else:
            alters.append("ALTER TABLE works ADD COLUMN grade VARCHAR(64) DEFAULT ''")
    for col, typedef in [
        ("tags", "VARCHAR(256) DEFAULT ''"),
        ("paper_link", "VARCHAR(512) DEFAULT ''"),
        ("github_link", "VARCHAR(512) DEFAULT ''"),
        ("video_link", "VARCHAR(512) DEFAULT ''"),
        ("user_id", "INTEGER"),
        ("is_hidden", "BOOLEAN DEFAULT 0"),
        ("reject_reason", "TEXT DEFAULT ''"),
        ("project_time", "VARCHAR(64) DEFAULT ''"),
        ("supervisor", "VARCHAR(64) DEFAULT ''"),
        ("technical_angle", "TEXT DEFAULT ''"),
        ("technical_angle_en", "TEXT DEFAULT ''"),
        ("summary_en", "TEXT DEFAULT ''"),
        ("video_intro", "TEXT DEFAULT ''"),
        ("video_intro_en", "TEXT DEFAULT ''"),
        ("milestones_en", "TEXT DEFAULT ''"),
        ("author_reflection_en", "TEXT DEFAULT ''"),
        ("activities_awards_en", "TEXT DEFAULT ''"),
        ("image_captions", "TEXT DEFAULT ''"),
        ("ppt_link", "VARCHAR(512) DEFAULT ''"),
        ("report_links", "TEXT DEFAULT ''"),
        ("activity_images", "TEXT DEFAULT ''"),
    ]:
        if col not in existing and col != "grade":
            alters.append(f"ALTER TABLE works ADD COLUMN {col} {typedef}")
    for sql in alters:
        try:
            db.session.execute(text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()


def _ensure_admin(app):
    if Admin.query.first():
        return
    admin = Admin(
        username=app.config["ADMIN_USERNAME"],
        password_hash=generate_password_hash(
            app.config["ADMIN_PASSWORD"], method="pbkdf2:sha256"
        ),
    )
    db.session.add(admin)
    db.session.commit()


def get_lang():
    lang = session.get("lang", Config.DEFAULT_LANGUAGE)
    return lang if lang in Config.LANGUAGES else Config.DEFAULT_LANGUAGE


def public_works_query():
    return Work.query.filter_by(status="approved", is_hidden=False)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )


def save_upload(file):
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit(".", 1)[1].lower()
    name = f"{uuid.uuid4().hex}.{ext}"
    from flask import current_app

    path = os.path.join(current_app.config["UPLOAD_FOLDER"], name)
    file.save(path)
    return f"uploads/{name}"


def is_admin_user():
    return current_user.is_authenticated and getattr(current_user, "is_admin", False)


def is_logged_in_user():
    return current_user.is_authenticated and not getattr(current_user, "is_admin", False)


def clear_any_login():
    """Ensure only one role (user or admin) is logged in at a time."""
    if current_user.is_authenticated:
        logout_user()


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_admin_user():
            return redirect(url_for("admin_login", next=request.url))
        return f(*args, **kwargs)

    return decorated


def user_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in_user():
            flash(get_text("login_required", get_lang()), "error")
            return redirect(url_for("user_login", next=request.url))
        return f(*args, **kwargs)

    return decorated


def video_embed_url(url):
    if not url:
        return None
    url = url.strip()
    m = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)", url)
    if m:
        return f"https://www.youtube.com/embed/{m.group(1)}"
    m = re.search(r"bilibili\.com/video/(BV[\w]+)", url)
    if m:
        return f"https://player.bilibili.com/player.html?bvid={m.group(1)}&high_quality=1"
    return None


def parse_milestones_from_form(form, suffix=""):
    items = []
    for i in range(1, 4):
        title = form.get(f"milestone_title_{i}{suffix}", "").strip()
        desc = form.get(f"milestone_desc_{i}{suffix}", "").strip()
        if title or desc:
            items.append({"title": title, "desc": desc})
    return items


def find_similar_works(work, limit=4):
    if not work.tag_list:
        return []
    q = public_works_query().filter(Work.id != work.id)
    conditions = [Work.tags.ilike(f"%{tag}%") for tag in work.tag_list]
    from sqlalchemy import or_

    return q.filter(or_(*conditions)).order_by(Work.created_at.desc()).limit(limit).all()


def register_routes(app):
    @app.before_request
    def set_language():
        lang_param = request.args.get("lang")
        if lang_param in Config.LANGUAGES:
            session["lang"] = lang_param

    @app.context_processor
    def inject_globals():
        lang = get_lang()

        def t(key, **kwargs):
            return get_text(key, lang, **kwargs)

        def cat_label(key):
            return Config.category_label(key, lang)

        categories = [(k, Config.category_label(k, lang)) for k, _ in Config.CATEGORIES]
        return {
            "t": t,
            "lang": lang,
            "categories": categories,
            "cat_label": cat_label,
            "is_admin": is_admin_user(),
            "is_user": is_logged_in_user(),
            "video_embed_url": video_embed_url,
        }

    @app.route("/set-lang/<lang_code>")
    def set_lang(lang_code):
        if lang_code in Config.LANGUAGES:
            session["lang"] = lang_code
        return redirect(request.referrer or url_for("index"))

    @app.route("/")
    def index():
        featured = public_works_query().order_by(Work.created_at.desc()).limit(6).all()
        gallery_works = public_works_query().order_by(Work.created_at.desc()).all()
        stats = {
            "total": public_works_query().count(),
            "pending": Work.query.filter_by(status="pending").count(),
            "authors": db.session.query(Work.author_name)
            .filter_by(status="approved", is_hidden=False)
            .distinct()
            .count(),
        }
        return render_template(
            "index.html",
            featured=featured,
            gallery_works=gallery_works,
            stats=stats,
        )

    @app.route("/gallery")
    def gallery():
        return redirect(url_for("index", _anchor="carousel"))

    @app.route("/archive")
    def archive():
        q = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()
        tag = request.args.get("tag", "").strip()
        query = public_works_query()
        if category:
            query = query.filter_by(category=category)
        if tag:
            query = query.filter(Work.tags.ilike(f"%{tag}%"))
        if q:
            like = f"%{q}%"
            query = query.filter(
                db.or_(
                    Work.title.ilike(like),
                    Work.summary.ilike(like),
                    Work.author_name.ilike(like),
                    Work.grade.ilike(like),
                    Work.tags.ilike(like),
                    Work.project_time.ilike(like),
                    Work.supervisor.ilike(like),
                    Work.technical_angle.ilike(like),
                )
            )
        works = query.order_by(Work.created_at.desc()).all()
        return render_template(
            "archive.html",
            works=works,
            q=q,
            category=category,
            tag=tag,
        )

    @app.route("/work/<int:work_id>")
    def work_detail(work_id):
        work = Work.query.get_or_404(work_id)
        if not work.is_public and not is_admin_user():
            abort(404)
        similar = find_similar_works(work)
        return render_template("work_detail.html", work=work, similar=similar)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if is_logged_in_user():
            return redirect(url_for("submit"))
        if is_admin_user():
            flash(get_text("admin_cannot_user_login", get_lang()), "error")
            return redirect(url_for("admin_dashboard"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            confirm = (
                request.form.get("password_confirm")
                or request.form.get("password2")
                or ""
            ).strip()
            lang = get_lang()
            errors = []
            if not email:
                errors.append("请填写邮箱" if lang == "zh" else "Email is required")
            if len(username) < 3:
                errors.append("用户名至少 3 个字符" if lang == "zh" else "Username must be at least 3 characters")
            if User.query.filter_by(username=username).first():
                errors.append("用户名已存在" if lang == "zh" else "Username already exists")
            if User.query.filter_by(email=email).first():
                errors.append("邮箱已注册" if lang == "zh" else "Email already registered")
            if len(password) < 6:
                errors.append("密码至少 6 位" if lang == "zh" else "Password must be at least 6 characters")
            if password != confirm:
                errors.append("两次密码不一致" if lang == "zh" else "Passwords do not match")
            if errors:
                for e in errors:
                    flash(e, "error")
                return render_template("register.html"), 400
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
            )
            db.session.add(user)
            db.session.commit()
            clear_any_login()
            login_user(user)
            flash("注册成功" if lang == "zh" else "Registration successful", "success")
            return redirect(url_for("submit"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def user_login():
        if is_logged_in_user():
            return redirect(url_for("submit"))
        if is_admin_user():
            flash(get_text("admin_cannot_user_login", get_lang()), "error")
            return redirect(url_for("admin_dashboard"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                clear_any_login()
                login_user(user)
                next_url = request.args.get("next") or url_for("submit")
                return redirect(next_url)
            flash(
                "用户名或密码错误" if get_lang() == "zh" else "Invalid username or password",
                "error",
            )
        return render_template("user/login.html")

    @app.route("/logout")
    def user_logout():
        if is_logged_in_user():
            logout_user()
        return redirect(url_for("index"))

    @app.route("/my-submissions")
    @user_required
    def my_submissions():
        works = (
            Work.query.filter_by(user_id=current_user.id)
            .order_by(Work.created_at.desc())
            .all()
        )
        return render_template("my_submissions.html", works=works)

    @app.route("/my-submissions/<int:work_id>")
    @user_required
    def my_submission_detail(work_id):
        work = Work.query.filter_by(id=work_id, user_id=current_user.id).first_or_404()
        return render_template("my_submission_detail.html", work=work)

    @app.route("/submit", methods=["GET", "POST"])
    @user_required
    def submit():
        if request.method == "POST":
            return _handle_submit()
        return render_template("submit.html")

    def _handle_submit():
        lang = get_lang()
        title = request.form.get("title", "").strip()
        project_time = request.form.get("project_time", "").strip()
        summary = request.form.get("summary", "").strip()
        summary_en = request.form.get("summary_en", "").strip()
        category = request.form.get("category", "").strip()
        tags = request.form.get("tags", "").strip()
        technical_angle = request.form.get("technical_angle", "").strip()
        technical_angle_en = request.form.get("technical_angle_en", "").strip()
        video_intro = request.form.get("video_intro", "").strip()
        video_intro_en = request.form.get("video_intro_en", "").strip()
        author_reflection = request.form.get("author_reflection", "").strip()
        author_reflection_en = request.form.get("author_reflection_en", "").strip()
        activities_awards = request.form.get("activities_awards", "").strip()
        activities_awards_en = request.form.get("activities_awards_en", "").strip()
        github_link = request.form.get("github_link", "").strip()
        ppt_link = request.form.get("ppt_link", "").strip()
        paper_link = request.form.get("paper_link", "").strip()
        report_links = request.form.get("report_links", "").strip()
        video_link = request.form.get("video_link", "").strip()
        author_name = request.form.get("author_name", "").strip()
        student_id = request.form.get("student_id", "").strip()
        grade = request.form.get("grade", "").strip()
        supervisor = request.form.get("supervisor", "").strip()
        contact = request.form.get("contact", "").strip()

        milestones = parse_milestones_from_form(request.form)
        milestones_en = parse_milestones_from_form(request.form, "_en")
        captions = request.form.getlist("image_caption")
        while len(captions) < len(request.files.getlist("images")):
            captions.append("")

        valid_cats = {c[0] for c in Config.CATEGORIES}
        req = lambda key: get_text(key, lang) + (" 必填" if lang == "zh" else " required")
        errors = []
        if not title:
            errors.append(req("label_title"))
        if not project_time:
            errors.append(req("label_project_time"))
        if not summary:
            errors.append(req("label_summary"))
        if not technical_angle:
            errors.append(req("label_technical_angle"))
        if category not in valid_cats:
            errors.append(get_text("label_category", lang))
        if not tags:
            errors.append(req("label_keywords"))
        if not author_name:
            errors.append(req("label_name"))
        if not student_id:
            errors.append(req("label_student_id"))
        if not grade:
            errors.append(req("label_grade"))
        if not contact:
            errors.append(req("label_contact"))
        if not video_link:
            errors.append(req("label_video"))
        if not github_link:
            errors.append(req("label_github_repo"))
        if not author_reflection:
            errors.append(req("label_reflection"))
        if not activities_awards:
            errors.append(req("label_activities"))
        if len(milestones) < 2:
            errors.append(get_text("milestone_min_error", lang))

        files = request.files.getlist("images")
        saved = [save_upload(f) for f in files]
        saved = [p for p in saved if p]
        if not saved:
            errors.append(get_text("label_project_images", lang))

        activity_saved = [
            save_upload(f) for f in request.files.getlist("activity_images")
        ]
        activity_saved = [p for p in activity_saved if p]

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("submit.html"), 400

        work = Work(
            title=title,
            project_time=project_time,
            summary=summary,
            summary_en=summary_en,
            description="",
            technical_angle=technical_angle,
            technical_angle_en=technical_angle_en,
            category=category,
            tags=tags,
            paper_link=paper_link,
            github_link=github_link,
            ppt_link=ppt_link,
            report_links=report_links,
            video_link=video_link,
            video_intro=video_intro,
            video_intro_en=video_intro_en,
            milestones=json.dumps(milestones, ensure_ascii=False),
            milestones_en=json.dumps(milestones_en, ensure_ascii=False) if milestones_en else "",
            author_reflection=author_reflection,
            author_reflection_en=author_reflection_en,
            activities_awards=activities_awards,
            activities_awards_en=activities_awards_en,
            cover_image=saved[0],
            images="|".join(saved),
            image_captions="|".join(
                (c.strip() if c else "") for c in captions[: len(saved)]
            ),
            activity_images="|".join(activity_saved),
            author_name=author_name,
            student_id=student_id,
            grade=grade,
            supervisor=supervisor,
            contact=contact,
            user_id=current_user.id,
            status="pending",
        )
        db.session.add(work)
        db.session.commit()
        flash(
            "投稿已提交，等待管理员审核" if lang == "zh" else "Submitted — awaiting admin review",
            "success",
        )
        return redirect(url_for("my_submissions"))

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if is_admin_user():
            return redirect(url_for("admin_dashboard"))
        if is_logged_in_user():
            flash(get_text("user_cannot_admin_login", get_lang()), "error")
            return redirect(url_for("index"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            admin = Admin.query.filter_by(username=username).first()
            if admin and check_password_hash(admin.password_hash, password):
                clear_any_login()
                login_user(admin)
                next_url = request.args.get("next") or url_for("admin_dashboard")
                return redirect(next_url)
            flash(
                "用户名或密码错误" if get_lang() == "zh" else "Invalid credentials",
                "error",
            )
        return render_template("admin/login.html")

    @app.route("/admin/logout")
    @admin_required
    def admin_logout():
        logout_user()
        return redirect(url_for("index"))

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        pending = Work.query.filter_by(status="pending").order_by(Work.created_at.asc()).all()
        approved = (
            Work.query.filter_by(status="approved")
            .order_by(Work.created_at.desc())
            .all()
        )
        rejected = (
            Work.query.filter_by(status="rejected")
            .order_by(Work.created_at.desc())
            .limit(10)
            .all()
        )
        return render_template(
            "admin/dashboard.html",
            pending=pending,
            approved=approved,
            rejected=rejected,
        )

    @app.route("/admin/review/<int:work_id>", methods=["GET", "POST"])
    @admin_required
    def admin_review(work_id):
        work = Work.query.get_or_404(work_id)
        if request.method == "POST":
            action = request.form.get("action")
            note = request.form.get("admin_note", "").strip()
            lang = get_lang()

            if action == "approve":
                work.status = "approved"
                work.is_hidden = False
                work.reject_reason = ""
                work.admin_note = note
                work.reviewed_at = datetime.utcnow()
                flash(f"{'已通过' if lang == 'zh' else 'Approved'}: {work.title}", "success")
            elif action == "reject":
                reject_reason = request.form.get("reject_reason", "").strip()
                if not reject_reason:
                    flash(
                        get_text("reject_reason_required", lang),
                        "error",
                    )
                    return render_template("admin/review.html", work=work), 400
                work.status = "rejected"
                work.reject_reason = reject_reason
                work.admin_note = note
                work.reviewed_at = datetime.utcnow()
                flash(f"{'已拒绝' if lang == 'zh' else 'Rejected'}: {work.title}", "success")
            elif action == "hide":
                work.is_hidden = True
                flash(f"{'已隐藏' if lang == 'zh' else 'Hidden'}: {work.title}", "success")
            elif action == "unhide":
                work.is_hidden = False
                flash(f"{'已取消隐藏' if lang == 'zh' else 'Unhidden'}: {work.title}", "success")
            elif action == "delete":
                _delete_work_files(work)
                db.session.delete(work)
                db.session.commit()
                flash(f"{'已删除' if lang == 'zh' else 'Deleted'}", "success")
                return redirect(url_for("admin_dashboard"))
            db.session.commit()
            if action in ("approve", "reject", "hide", "unhide"):
                return redirect(url_for("admin_dashboard"))
        return render_template("admin/review.html", work=work)


def _delete_work_files(work):
    from flask import current_app

    for img in work.all_image_paths():
        full = os.path.join(current_app.root_path, "static", img)
        if os.path.isfile(full):
            try:
                os.remove(full)
            except OSError:
                pass


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)
