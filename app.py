"""
АИС стоматологической клиники ORDENTIST.
python init_db.py  →  python app.py  →  http://127.0.0.1:5000/
"""

import os
import secrets
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, send_from_directory,
    request, redirect, url_for, session, flash, g, jsonify,
)
from werkzeug.utils import secure_filename

from config import Config
from models import (
    db, User, Patient, Doctor, Office, Appointment, MedicalHistory,
    Achievement, PatientAchievement, Service,
)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "images", "doctors")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def create_app():
    app = Flask(__name__, template_folder="templates")
    app.config.from_object(Config)
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    db.init_app(app)
    register_routes(app)
    return app


# ── helpers ──────────────────────────────────────────────────────────────────

def current_user():
    if not hasattr(g, "_cu"):
        uid = session.get("user_id")
        g._cu = User.query.get(uid) if uid else None
    return g._cu


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if current_user() is None:
            return redirect(url_for("login"))
        return view(*a, **kw)
    return wrapped


def role_required(*roles):
    def dec(view):
        @wraps(view)
        def wrapped(*a, **kw):
            u = current_user()
            if u is None:
                return redirect(url_for("login"))
            if u.role not in roles:
                flash("Недостаточно прав.", "error")
                return redirect(url_for("cabinet"))
            return view(*a, **kw)
        return wrapped
    return dec


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_patient_achievements(patient_id):
    all_ach = Achievement.query.order_by(Achievement.id_achievement).all()
    pm = {pa.achievement_id: pa
          for pa in PatientAchievement.query.filter_by(patient_id=patient_id).all()}
    result = []
    for ach in all_ach:
        pa = pm.get(ach.id_achievement)
        result.append({
            "title": ach.title, "desc": ach.description,
            "icon": ach.icon, "total": ach.total,
            "progress": pa.progress if pa else 0,
            "unlocked": pa.unlocked if pa else False,
        })
    return result


def update_achievements(patient_id):
    visits = Appointment.query.filter_by(patient_id=patient_id).count()
    histories = MedicalHistory.query.filter_by(patient_id=patient_id).all()
    teeth = len(histories)
    cleanings = sum(1 for h in histories if h.diagnosis and
                    any(w in h.diagnosis.lower() for w in ["гигиен", "чистк", "air flow"]))
    mapping = {
        "first_visit":   (min(visits, 1), 1),
        "heal_1_tooth":  (min(teeth, 1), 1),
        "heal_5_teeth":  (min(teeth, 5), 5),
        "heal_10_teeth": (min(teeth, 10), 10),
        "clean_3":       (min(cleanings, 3), 3),
        "punctual":      (min(visits, 5), 5),
    }
    for code, (prog, total) in mapping.items():
        ach = Achievement.query.filter_by(code=code).first()
        if not ach:
            continue
        pa = PatientAchievement.query.filter_by(
            patient_id=patient_id, achievement_id=ach.id_achievement).first()
        if not pa:
            pa = PatientAchievement(patient_id=patient_id,
                                    achievement_id=ach.id_achievement)
            db.session.add(pa)
        # Если ачивка уже разблокирована — прогресс = total (не сбрасываем)
        if pa.unlocked_at:
            pa.progress = total
        else:
            pa.progress = prog
            if prog >= total:
                pa.unlocked_at = datetime.utcnow()
    db.session.commit()


def _parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _appt_to_dict(a):
    return {
        "id": a.id_appointment,
        "date": a.appointment_date.strftime("%d.%m.%Y") if a.appointment_date else "—",
        "date_iso": a.appointment_date.isoformat() if a.appointment_date else "",
        "time": a.appointment_time.strftime("%H:%M") if a.appointment_time else "",
        "doctor": a.doctor.full_name if a.doctor else "—",
        "doctor_id": a.doctor_id,
        "patient": a.patient.full_name if a.patient else "—",
        "patient_id": a.patient_id,
        "office": a.office.office_number if a.office else "—",
        "service": a.service.name if a.service else "Приём",
        "status": a.status,
    }


def _build_stats(user, appointments):
    if user.role == "patient":
        total_v = Appointment.query.filter_by(patient_id=user.patient_id).count() if user.patient_id else 0
        hist_c = MedicalHistory.query.filter_by(patient_id=user.patient_id).count() if user.patient_id else 0
        ach_l = get_patient_achievements(user.patient_id) if user.patient_id else []
        unlocked = sum(1 for a in ach_l if a["unlocked"])
        next_a = next((a["date"] for a in appointments if a["status"] == "scheduled"), "—")
        return {"visits": total_v, "teeth_healed": hist_c,
                "achievements": f"{unlocked} / {len(ach_l)}", "next_appt": next_a}
    elif user.role == "doctor":
        today = date.today()
        tc = Appointment.query.filter_by(doctor_id=user.doctor_id).filter(
            Appointment.appointment_date == today).count() if user.doctor_id else 0
        tp = db.session.query(db.func.count(db.distinct(Appointment.patient_id))).filter_by(
            doctor_id=user.doctor_id).scalar() if user.doctor_id else 0
        return {"today": tc, "total_patients": tp,
                "experience": user.doctor.experience if user.doctor else 0, "rating": "4.9"}
    elif user.role == "manager":
        today = date.today()
        return {
            "today_appts": Appointment.query.filter(Appointment.appointment_date == today).count(),
            "total_doctors": Doctor.query.count(),
            "total_patients": Patient.query.count(),
            "offices": Office.query.count(),
        }
    elif user.role == "admin":
        return {
            "users": User.query.count(),
            "doctors": Doctor.query.count(),
            "patients": Patient.query.count(),
            "appointments": Appointment.query.count(),
        }
    return {}


def register_routes(app):

    # ── Публичные страницы ────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return render_template("main.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/prices")
    def prices():
        services = Service.query.order_by(Service.category, Service.name).all()
        # Группируем по категории
        categories = {}
        for s in services:
            cat = s.category or "Прочее"
            categories.setdefault(cat, []).append(s)
        return render_template("prices.html", categories=categories)

    # ── Авторизация ───────────────────────────────────────────────────────────

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            lv = request.form.get("login", "").strip()
            pw = request.form.get("password", "")
            user = User.query.filter(
                (User.email == lv) | (User.phone == lv)).first()
            if user and user.check_password(pw):
                session["user_id"] = user.id_user
                return redirect(url_for("cabinet"))
            return render_template("login.html", error="Неверный логин или пароль")
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            f = request.form
            errors = {}
            if not f.get("first_name", "").strip():
                errors["first_name"] = "Введите имя"
            if not f.get("last_name", "").strip():
                errors["last_name"] = "Введите фамилию"
            email = f.get("email", "").strip()
            if not email or "@" not in email:
                errors["email"] = "Введите корректный email"
            elif User.query.filter_by(email=email).first():
                errors["email"] = "Email уже зарегистрирован"
            phone = f.get("phone", "").strip()
            if not phone:
                errors["phone"] = "Введите телефон"
            pw = f.get("password", "")
            pw2 = f.get("password2", "")
            if len(pw) < 6:
                errors["password"] = "Минимум 6 символов"
            elif pw != pw2:
                errors["password2"] = "Пароли не совпадают"
            if errors:
                return render_template("register.html", errors=errors, form=f)

            patient = Patient(
                first_name=f.get("first_name"),
                middle_name=f.get("middle_name"),
                last_name=f.get("last_name"),
                phone=phone,
                birth_date=_parse_date(f.get("birth_date")),
            )
            db.session.add(patient)
            db.session.flush()
            user = User(email=email, phone=phone, role="patient",
                        patient_id=patient.id_patient)
            user.set_password(pw)
            db.session.add(user)
            db.session.commit()
            session["user_id"] = user.id_user
            flash("Добро пожаловать! Аккаунт создан.", "success")
            return redirect(url_for("cabinet"))
        return render_template("register.html", errors={}, form={})

    @app.route("/logout")
    def logout():
        session.pop("user_id", None)
        return redirect(url_for("index"))

    # ── Восстановление пароля ─────────────────────────────────────────────────

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            user = User.query.filter_by(email=email).first()
            if user:
                token = secrets.token_hex(32)
                user.reset_token = token
                user.reset_token_exp = datetime.utcnow() + timedelta(hours=1)
                db.session.commit()
                reset_url = url_for("reset_password", token=token, _external=True)
                flash(f"Ссылка для сброса пароля (скопируйте): {reset_url}", "info")
            else:
                flash("Если такой email зарегистрирован, ссылка отправлена.", "info")
            return redirect(url_for("forgot_password"))
        return render_template("forgot_password.html")

    @app.route("/reset-password/<token>", methods=["GET", "POST"])
    def reset_password(token):
        user = User.query.filter_by(reset_token=token).first()
        if not user or not user.reset_token_exp or user.reset_token_exp < datetime.utcnow():
            flash("Ссылка недействительна или устарела.", "error")
            return redirect(url_for("login"))
        if request.method == "POST":
            pw = request.form.get("password", "")
            pw2 = request.form.get("password2", "")
            if len(pw) < 6:
                return render_template("reset_password.html", token=token,
                                       error="Минимум 6 символов")
            if pw != pw2:
                return render_template("reset_password.html", token=token,
                                       error="Пароли не совпадают")
            user.set_password(pw)
            user.reset_token = None
            user.reset_token_exp = None
            db.session.commit()
            flash("Пароль успешно изменён. Войдите с новым паролем.", "success")
            return redirect(url_for("login"))
        return render_template("reset_password.html", token=token, error=None)

    # ── Личный кабинет ────────────────────────────────────────────────────────

    @app.route("/cabinet")
    @login_required
    def cabinet():
        user = current_user()

        # Уведомление о ближайшем приёме
        notifications = []
        if user.role == "patient" and user.patient_id:
            upcoming = Appointment.query.filter_by(
                patient_id=user.patient_id, status="scheduled"
            ).filter(
                Appointment.appointment_date >= date.today(),
                Appointment.appointment_date <= date.today() + timedelta(days=2)
            ).order_by(Appointment.appointment_date, Appointment.appointment_time).first()
            if upcoming:
                notifications.append({
                    "type": "info",
                    "text": f"Напоминание: у вас запись {upcoming.appointment_date.strftime('%d.%m.%Y')}"
                            f" в {upcoming.appointment_time.strftime('%H:%M') if upcoming.appointment_time else '—'}"
                            f" к врачу {upcoming.doctor.full_name if upcoming.doctor else '—'}."
                })
        elif user.role == "doctor" and user.doctor_id:
            today_count = Appointment.query.filter_by(
                doctor_id=user.doctor_id, status="scheduled"
            ).filter(Appointment.appointment_date == date.today()).count()
            if today_count:
                notifications.append({
                    "type": "info",
                    "text": f"Сегодня у вас {today_count} запланированных приёмов."
                })

        # Записи
        appts_q = Appointment.query
        if user.role == "patient" and user.patient_id:
            appts_q = appts_q.filter_by(patient_id=user.patient_id)
        elif user.role == "doctor" and user.doctor_id:
            appts_q = appts_q.filter_by(doctor_id=user.doctor_id)
        appointments = [_appt_to_dict(a) for a in
                        appts_q.order_by(Appointment.appointment_date,
                                         Appointment.appointment_time).limit(30).all()]

        # История
        histories = []
        hq = MedicalHistory.query
        if user.role == "patient" and user.patient_id:
            hq = hq.filter_by(patient_id=user.patient_id)
        elif user.role == "doctor" and user.doctor_id:
            hq = hq.filter_by(doctor_id=user.doctor_id)
        for h in hq.order_by(MedicalHistory.visit_date.desc()).limit(30).all():
            histories.append({
                "id": h.id_history,
                "date": h.visit_date.strftime("%d.%m.%Y") if h.visit_date else "—",
                "diagnosis": h.diagnosis or "—",
                "treatment": h.treatment or "—",
                "doctor": h.doctor.full_name if h.doctor else "—",
                "patient": h.patient.full_name if h.patient else "—",
            })

        # Ачивки
        achievements = []
        if user.role == "patient" and user.patient_id:
            update_achievements(user.patient_id)
            achievements = get_patient_achievements(user.patient_id)

        stats = _build_stats(user, appointments)
        doctors = Doctor.query.order_by(Doctor.last_name).all()
        offices = Office.query.order_by(Office.office_number).all()
        services = Service.query.order_by(Service.name).all()
        patients = Patient.query.order_by(Patient.last_name).all() \
            if user.role in ("manager", "admin", "doctor") else []

        # Прайс-лист сгруппированный по категориям
        price_categories = {}
        for s in Service.query.order_by(Service.category, Service.name).all():
            cat = s.category or "Прочее"
            price_categories.setdefault(cat, []).append(s)

        ctx = {
            "user": {
                "first_name": user.first_name,
                "middle_name": user.middle_name,
                "last_name": user.last_name,
                "phone": user.phone or (user.patient.phone if user.patient else ""),
                "email": user.email,
                "role": user.role,
                "role_label": user.role_label,
                "experience": user.doctor.experience if user.doctor else None,
                "qualification": user.doctor.qualification if user.doctor else None,
                "photo": user.doctor.photo if user.doctor else None,
            },
            "achievements": achievements,
            "appointments": appointments,
            "histories": histories,
            "stats": stats,
            "doctors": doctors,
            "offices": offices,
            "services": services,
            "patients": patients,
            "today_iso": date.today().isoformat(),
            "notifications": notifications,
            "price_categories": price_categories,
        }
        return render_template("cabinet.html", **ctx)

    # ── Завершение приёма (врач) ──────────────────────────────────────────────

    @app.route("/cabinet/appointment/<int:appt_id>/complete", methods=["POST"])
    @login_required
    def cabinet_appointment_complete(appt_id):
        user = current_user()
        appt = Appointment.query.get_or_404(appt_id)
        if user.role == "doctor" and appt.doctor_id != user.doctor_id:
            flash("Нет доступа.", "error")
            return redirect(url_for("cabinet") + "#appointments")
        if user.role not in ("doctor", "manager", "admin"):
            flash("Нет доступа.", "error")
            return redirect(url_for("cabinet") + "#appointments")
        appt.status = "completed"
        db.session.commit()
        flash("Приём завершён.", "success")
        return redirect(url_for("cabinet") + "#appointments")

    # ── Новая запись ──────────────────────────────────────────────────────────

    @app.route("/cabinet/appointment/new", methods=["POST"])
    @login_required
    def cabinet_appointment_new():
        user = current_user()
        f = request.form
        doctor_id = f.get("doctor_id") or None
        office_id = f.get("office_id") or None
        service_id = f.get("service_id") or None
        appt_date = _parse_date(f.get("appointment_date"))
        appt_time = None
        ts = f.get("appointment_time", "").strip()
        if ts:
            try:
                from datetime import time as dtime
                p = ts.split(":")
                appt_time = dtime(int(p[0]), int(p[1]))
            except Exception:
                pass
        patient_id = user.patient_id if user.role == "patient" else (f.get("patient_id") or None)
        if not patient_id or not appt_date:
            flash("Заполните обязательные поля: пациент и дата.", "error")
            return redirect(url_for("cabinet") + "#new-appointment")
        db.session.add(Appointment(
            patient_id=patient_id, doctor_id=doctor_id, office_id=office_id,
            service_id=service_id, appointment_date=appt_date,
            appointment_time=appt_time, status="scheduled",
        ))
        db.session.commit()
        flash("Запись успешно создана.", "success")
        return redirect(url_for("cabinet") + "#appointments")

    # ── Отмена записи ─────────────────────────────────────────────────────────

    @app.route("/cabinet/appointment/<int:appt_id>/cancel", methods=["POST"])
    @login_required
    def cabinet_appointment_cancel(appt_id):
        user = current_user()
        appt = Appointment.query.get_or_404(appt_id)
        if user.role == "patient" and appt.patient_id != user.patient_id:
            flash("Нет доступа.", "error")
            return redirect(url_for("cabinet") + "#appointments")
        appt.status = "cancelled"
        db.session.commit()
        flash("Запись отменена.", "success")
        return redirect(url_for("cabinet") + "#appointments")

    # ── История лечения ───────────────────────────────────────────────────────

    @app.route("/cabinet/history/add", methods=["POST"])
    @login_required
    @role_required("doctor", "manager", "admin")
    def cabinet_history_add():
        f = request.form
        user = current_user()
        patient_id = f.get("patient_id") or None
        doctor_id = f.get("doctor_id") or (user.doctor_id if user.role == "doctor" else None)
        visit_date = _parse_date(f.get("visit_date"))
        if not patient_id or not visit_date:
            flash("Заполните обязательные поля.", "error")
            return redirect(url_for("cabinet") + "#history")
        db.session.add(MedicalHistory(
            patient_id=patient_id, doctor_id=doctor_id,
            diagnosis=f.get("diagnosis", "").strip(),
            treatment=f.get("treatment", "").strip(),
            visit_date=visit_date,
        ))
        db.session.commit()
        update_achievements(int(patient_id))
        flash("Запись в историю добавлена.", "success")
        return redirect(url_for("cabinet") + "#history")

    # ── Профиль ───────────────────────────────────────────────────────────────

    @app.route("/cabinet/profile/edit", methods=["POST"])
    @login_required
    def cabinet_profile_edit():
        user = current_user()
        f = request.form
        if user.patient:
            user.patient.first_name = f.get("first_name") or user.patient.first_name
            user.patient.middle_name = f.get("middle_name") or user.patient.middle_name
            user.patient.last_name = f.get("last_name") or user.patient.last_name
            user.patient.phone = f.get("phone") or user.patient.phone
            bd = _parse_date(f.get("birth_date"))
            if bd:
                user.patient.birth_date = bd
        elif user.doctor:
            user.doctor.first_name = f.get("first_name") or user.doctor.first_name
            user.doctor.middle_name = f.get("middle_name") or user.doctor.middle_name
            user.doctor.last_name = f.get("last_name") or user.doctor.last_name
        new_email = f.get("email", "").strip()
        if new_email and new_email != user.email:
            if User.query.filter_by(email=new_email).first():
                flash("Этот email уже занят.", "error")
                return redirect(url_for("cabinet") + "#profile")
            user.email = new_email
        if f.get("phone"):
            user.phone = f.get("phone")
        db.session.commit()
        flash("Профиль обновлён.", "success")
        return redirect(url_for("cabinet") + "#profile")

    # ── Загрузка фото врача ───────────────────────────────────────────────────

    @app.route("/cabinet/doctor/photo", methods=["POST"])
    @login_required
    def cabinet_doctor_photo():
        user = current_user()
        if not user.doctor:
            flash("Только врачи могут загружать фото.", "error")
            return redirect(url_for("cabinet") + "#profile")
        file = request.files.get("photo")
        if not file or file.filename == "":
            flash("Файл не выбран.", "error")
            return redirect(url_for("cabinet") + "#profile")
        if not allowed_file(file.filename):
            flash("Допустимые форматы: PNG, JPG, JPEG, WEBP.", "error")
            return redirect(url_for("cabinet") + "#profile")
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = secure_filename(f"doctor_{user.doctor_id}.{ext}")
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        user.doctor.photo = filename
        db.session.commit()
        flash("Фото обновлено.", "success")
        return redirect(url_for("cabinet") + "#profile")

    # ── Смена пароля ──────────────────────────────────────────────────────────

    @app.route("/cabinet/password/change", methods=["POST"])
    @login_required
    def cabinet_password_change():
        user = current_user()
        f = request.form
        if not user.check_password(f.get("old_password", "")):
            flash("Неверный текущий пароль.", "error")
            return redirect(url_for("cabinet") + "#settings")
        pw = f.get("new_password", "")
        if len(pw) < 6:
            flash("Новый пароль — минимум 6 символов.", "error")
            return redirect(url_for("cabinet") + "#settings")
        if pw != f.get("new_password2", ""):
            flash("Пароли не совпадают.", "error")
            return redirect(url_for("cabinet") + "#settings")
        user.set_password(pw)
        db.session.commit()
        flash("Пароль изменён.", "success")
        return redirect(url_for("cabinet") + "#settings")

    # ── API: слоты ────────────────────────────────────────────────────────────

    @app.route("/api/slots")
    @login_required
    def api_slots():
        doctor_id = request.args.get("doctor_id")
        appt_date = request.args.get("date")
        if not doctor_id or not appt_date:
            return jsonify([])
        busy = {
            a.appointment_time.strftime("%H:%M")
            for a in Appointment.query.filter_by(
                doctor_id=doctor_id,
                appointment_date=_parse_date(appt_date)
            ).filter(Appointment.status != "cancelled").all()
            if a.appointment_time
        }
        slots = [f"{h:02d}:{m:02d}" for h in range(8, 20) for m in (0, 30)]
        return jsonify([s for s in slots if s not in busy])

    # ── API: поиск пациентов ──────────────────────────────────────────────────

    @app.route("/cabinet/patients")
    @login_required
    @role_required("manager", "admin", "doctor")
    def cabinet_patients():
        q = request.args.get("q", "").strip()
        query = Patient.query
        if q:
            like = f"%{q}%"
            query = query.filter(
                db.or_(
                    Patient.last_name.ilike(like),
                    Patient.first_name.ilike(like),
                    Patient.phone.ilike(like),
                )
            )
        patients = query.order_by(Patient.last_name).limit(100).all()
        result = []
        for p in patients:
            last_h = MedicalHistory.query.filter_by(patient_id=p.id_patient)\
                .order_by(MedicalHistory.visit_date.desc()).first()
            result.append({
                "id": p.id_patient,
                "name": p.full_name,
                "phone": p.phone or "—",
                "birth_date": p.birth_date.strftime("%d.%m.%Y") if p.birth_date else "—",
                "visits": Appointment.query.filter_by(patient_id=p.id_patient).count(),
                "last_visit": last_h.visit_date.strftime("%d.%m.%Y")
                              if last_h and last_h.visit_date else "—",
            })
        return jsonify(result)

    # ── API: поиск записей ────────────────────────────────────────────────────

    @app.route("/api/appointments")
    @login_required
    @role_required("manager", "admin")
    def api_appointments():
        q = request.args.get("q", "").strip()
        status = request.args.get("status", "")
        query = Appointment.query
        if status:
            query = query.filter_by(status=status)
        if q:
            like = f"%{q}%"
            query = query.join(Patient, isouter=True).join(Doctor, isouter=True).filter(
                db.or_(
                    Patient.last_name.ilike(like),
                    Patient.first_name.ilike(like),
                    Doctor.last_name.ilike(like),
                )
            )
        appts = query.order_by(Appointment.appointment_date.desc()).limit(50).all()
        return jsonify([_appt_to_dict(a) for a in appts])

    # ── Управление: добавить врача ────────────────────────────────────────────

    @app.route("/cabinet/doctor/add", methods=["POST"])
    @login_required
    @role_required("manager", "admin")
    def cabinet_doctor_add():
        f = request.form
        email = f.get("email", "").strip()
        if not email:
            flash("Email обязателен.", "error")
            return redirect(url_for("cabinet") + "#manage")
        if User.query.filter_by(email=email).first():
            flash("Пользователь с таким email уже существует.", "error")
            return redirect(url_for("cabinet") + "#manage")

        # Роль: admin может выбрать любую, менеджер — только doctor
        cur = current_user()
        role_override = f.get("role_override", "doctor")
        if cur.role != "admin":
            role_override = "doctor"

        doctor = None
        if role_override == "doctor":
            doctor = Doctor(
                first_name=f.get("first_name"), middle_name=f.get("middle_name"),
                last_name=f.get("last_name"), qualification=f.get("qualification"),
                experience=int(f.get("experience") or 0),
            )
            db.session.add(doctor)
            db.session.flush()

        u = User(
            email=email,
            phone=f.get("phone"),
            role=role_override,
            doctor_id=doctor.id_doctor if doctor else None,
        )
        u.set_password(f.get("password") or "changeme")
        db.session.add(u)
        db.session.commit()

        name = doctor.full_name if doctor else email
        flash(f"Сотрудник {name} добавлен с ролью «{role_override}».", "success")
        return redirect(url_for("cabinet") + "#manage")

    # ── Управление: удалить пользователя (только admin) ──────────────────────

    @app.route("/cabinet/user/<int:uid>/delete", methods=["POST"])
    @login_required
    @role_required("admin")
    def cabinet_user_delete(uid):
        user = current_user()
        if uid == user.id_user:
            flash("Нельзя удалить себя.", "error")
            return redirect(url_for("cabinet") + "#manage")
        u = User.query.get_or_404(uid)
        db.session.delete(u)
        db.session.commit()
        flash("Пользователь удалён.", "success")
        return redirect(url_for("cabinet") + "#manage")

    # ── Управление: список всех пользователей (admin) ────────────────────────

    @app.route("/api/users")
    @login_required
    @role_required("admin")
    def api_users():
        users = User.query.order_by(User.role, User.email).all()
        return jsonify([{
            "id": u.id_user,
            "email": u.email,
            "phone": u.phone or "—",
            "role": u.role,
            "role_label": u.role_label,
            "name": f"{u.last_name} {u.first_name}".strip() or u.email,
            "created": u.created_at.strftime("%d.%m.%Y") if u.created_at else "—",
        } for u in users])

    # ── Карточка пациента ────────────────────────────────────────────────────

    @app.route("/patient/<int:patient_id>")
    @login_required
    @role_required("doctor", "manager", "admin")
    def patient_card(patient_id):
        patient = Patient.query.get_or_404(patient_id)
        histories = []
        for h in MedicalHistory.query.filter_by(patient_id=patient_id)\
                .order_by(MedicalHistory.visit_date.desc()).all():
            histories.append({
                "date": h.visit_date.strftime("%d.%m.%Y") if h.visit_date else "—",
                "diagnosis": h.diagnosis or "—",
                "treatment": h.treatment or "—",
                "doctor": h.doctor.full_name if h.doctor else "—",
            })
        appointments = [_appt_to_dict(a) for a in
                        Appointment.query.filter_by(patient_id=patient_id)
                        .order_by(Appointment.appointment_date.desc()).all()]
        return render_template("patient_card.html",
                               patient=patient,
                               histories=histories,
                               appointments=appointments)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("404.html", code=403,
                               message="Доступ запрещён"), 403

    # ── Статика ───────────────────────────────────────────────────────────────

    @app.route("/css/<path:filename>")
    def serve_css(filename): return send_from_directory("css", filename)

    @app.route("/js/<path:filename>")
    def serve_js(filename): return send_from_directory("js", filename)

    @app.route("/images/<path:filename>")
    def serve_images(filename): return send_from_directory("images", filename)


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
