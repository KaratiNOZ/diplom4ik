"""
Демо-аккаунты:
    patient@demo.ru / 1234   — пациент
    doctor@demo.ru  / 1234   — врач
    manager@demo.ru / 1234   — менеджер
    admin@demo.ru   / 1234   — администратор
"""

from datetime import datetime, date, time

from app import app
from models import (
    db, User, Patient, Doctor, Office, Appointment,
    MedicalHistory, Achievement, PatientAchievement, Service,
)


ACHIEVEMENTS_SEED = [
    {"code": "first_visit",   "title": "Первый визит",      "description": "Пришёл к стоматологу впервые",      "icon": "i-tooth",   "total": 1},
    {"code": "heal_1_tooth",  "title": "Вылечить 1 зуб",    "description": "Установить первую пломбу",          "icon": "i-medal",   "total": 1},
    {"code": "heal_5_teeth",  "title": "Вылечить 5 зубов",  "description": "Серьёзная работа над улыбкой",      "icon": "i-trophy",  "total": 5},
    {"code": "heal_10_teeth", "title": "Вылечить 10 зубов", "description": "Король стоматологии",               "icon": "i-trophy",  "total": 10},
    {"code": "clean_3",       "title": "Чистюля",           "description": "3 профессиональные чистки за год",  "icon": "i-sparkle", "total": 3},
    {"code": "no_fear",       "title": "Без страха",        "description": "Лечение без обезболивания",         "icon": "i-shield",  "total": 1},
    {"code": "punctual",      "title": "Пунктуальный",      "description": "5 визитов без опозданий",           "icon": "i-clock",   "total": 5},
    {"code": "whitening",     "title": "Идеальная улыбка",  "description": "Пройти курс отбеливания",           "icon": "i-star",    "total": 1},
]

SERVICES_SEED = [
    {"name": "Консультация стоматолога",        "price": 0,     "category": "Консультация"},
    {"name": "Лечение кариеса",                 "price": 2500,  "category": "Терапия"},
    {"name": "Лечение пульпита",                "price": 5500,  "category": "Терапия"},
    {"name": "Лечение периодонтита",            "price": 6500,  "category": "Терапия"},
    {"name": "Удаление зуба (простое)",         "price": 2000,  "category": "Хирургия"},
    {"name": "Удаление зуба (сложное)",         "price": 4500,  "category": "Хирургия"},
    {"name": "Имплантация зуба",                "price": 35000, "category": "Имплантология"},
    {"name": "Профессиональная гигиена (Air Flow)", "price": 4500, "category": "Гигиена"},
    {"name": "Ультразвуковая чистка",           "price": 3000,  "category": "Гигиена"},
    {"name": "Отбеливание Zoom",                "price": 15000, "category": "Эстетика"},
    {"name": "Установка брекетов",              "price": 80000, "category": "Ортодонтия"},
    {"name": "Элайнеры (курс)",                 "price": 120000,"category": "Ортодонтия"},
    {"name": "Детский осмотр",                  "price": 800,   "category": "Детская стоматология"},
    {"name": "Лечение молочного зуба",          "price": 1800,  "category": "Детская стоматология"},
    {"name": "Рентген (прицельный)",            "price": 500,   "category": "Диагностика"},
    {"name": "Панорамный снимок",               "price": 1200,  "category": "Диагностика"},
]


def seed_achievements():
    for data in ACHIEVEMENTS_SEED:
        if not Achievement.query.filter_by(code=data["code"]).first():
            db.session.add(Achievement(**data))
    db.session.commit()
    print(f"  Ачивки: {Achievement.query.count()} записей.")


def seed_services():
    if Service.query.count() == 0:
        for data in SERVICES_SEED:
            db.session.add(Service(**data))
        db.session.commit()
    print(f"  Услуги: {Service.query.count()} записей.")


def seed_offices():
    if Office.query.count() == 0:
        for n in (1, 2, 3, 4, 5):
            db.session.add(Office(office_number=n))
        db.session.commit()
    print(f"  Кабинеты: {Office.query.count()} шт.")


def seed_demo_users():
    # --- Пациент ---
    if not User.query.filter_by(email="patient@demo.ru").first():
        patient = Patient(
            first_name="Алексей", middle_name="Сергеевич", last_name="Петров",
            phone="+79991234567", birth_date=date(1995, 3, 14),
        )
        db.session.add(patient)
        db.session.flush()

        u = User(email="patient@demo.ru", phone=patient.phone,
                 role="patient", patient_id=patient.id_patient)
        u.set_password("1234")
        db.session.add(u)
        db.session.flush()

        # Демо-история лечения
        doctor = Doctor.query.first()
        svc_caries = Service.query.filter_by(name="Лечение кариеса").first()
        svc_hygiene = Service.query.filter_by(name="Профессиональная гигиена (Air Flow)").first()
        office = Office.query.first()

        histories = [
            MedicalHistory(patient_id=patient.id_patient,
                           doctor_id=doctor.id_doctor if doctor else None,
                           diagnosis="Средний кариес зуба 26",
                           treatment="Препарирование, установка композитной пломбы",
                           visit_date=date(2025, 10, 12)),
            MedicalHistory(patient_id=patient.id_patient,
                           doctor_id=doctor.id_doctor if doctor else None,
                           diagnosis="Профессиональная гигиена полости рта",
                           treatment="Air Flow + ультразвуковая чистка",
                           visit_date=date(2025, 7, 3)),
            MedicalHistory(patient_id=patient.id_patient,
                           doctor_id=doctor.id_doctor if doctor else None,
                           diagnosis="Консультация ортодонта",
                           treatment="Рекомендованы элайнеры для коррекции прикуса",
                           visit_date=date(2025, 2, 15)),
            MedicalHistory(patient_id=patient.id_patient,
                           doctor_id=doctor.id_doctor if doctor else None,
                           diagnosis="Лечение пульпита зуба 36",
                           treatment="Эндодонтическое лечение, пломбирование каналов",
                           visit_date=date(2024, 11, 20)),
        ]
        for h in histories:
            db.session.add(h)

        # Демо-записи на приём
        if doctor and office:
            appts = [
                Appointment(patient_id=patient.id_patient, doctor_id=doctor.id_doctor,
                            office_id=office.id_office, service_id=svc_caries.id_service if svc_caries else None,
                            appointment_date=date(2026, 6, 10), appointment_time=time(10, 0),
                            status="scheduled"),
                Appointment(patient_id=patient.id_patient, doctor_id=doctor.id_doctor,
                            office_id=office.id_office, service_id=svc_hygiene.id_service if svc_hygiene else None,
                            appointment_date=date(2026, 6, 25), appointment_time=time(14, 30),
                            status="scheduled"),
            ]
            for a in appts:
                db.session.add(a)

        db.session.commit()

        # Ачивки
        progress = {
            "first_visit":   (1, True),
            "heal_1_tooth":  (1, True),
            "heal_5_teeth":  (4, False),
            "heal_10_teeth": (4, False),
            "clean_3":       (2, False),
            "no_fear":       (1, True),
            "punctual":      (5, True),
            "whitening":     (0, False),
        }
        for code, (prog, unlocked) in progress.items():
            ach = Achievement.query.filter_by(code=code).first()
            if ach:
                db.session.add(PatientAchievement(
                    patient_id=patient.id_patient,
                    achievement_id=ach.id_achievement,
                    progress=prog,
                    unlocked_at=datetime.utcnow() if unlocked else None,
                ))
        db.session.commit()
        print("  + patient@demo.ru / 1234")

    # --- Врач 1 ---
    if not User.query.filter_by(email="doctor@demo.ru").first():
        doctor = Doctor(
            first_name="Иван", middle_name="Иванович", last_name="Иванов",
            qualification="Стоматолог-терапевт", experience=12,
        )
        db.session.add(doctor)
        db.session.flush()
        u = User(email="doctor@demo.ru", phone="+79992223344",
                 role="doctor", doctor_id=doctor.id_doctor)
        u.set_password("1234")
        db.session.add(u)
        db.session.commit()
        print("  + doctor@demo.ru / 1234")

    # --- Врач 2 ---
    if not User.query.filter_by(email="doctor2@demo.ru").first():
        doctor2 = Doctor(
            first_name="Анна", middle_name="Сергеевна", last_name="Петрова",
            qualification="Ортодонт", experience=9,
        )
        db.session.add(doctor2)
        db.session.flush()
        u2 = User(email="doctor2@demo.ru", phone="+79993334455",
                  role="doctor", doctor_id=doctor2.id_doctor)
        u2.set_password("1234")
        db.session.add(u2)
        db.session.commit()
        print("  + doctor2@demo.ru / 1234")

    # --- Менеджер ---
    if not User.query.filter_by(email="manager@demo.ru").first():
        u = User(email="manager@demo.ru", phone="+79995556677", role="manager")
        u.set_password("1234")
        db.session.add(u)
        db.session.commit()
        print("  + manager@demo.ru / 1234")

    # --- Администратор ---
    if not User.query.filter_by(email="admin@demo.ru").first():
        u = User(email="admin@demo.ru", phone="+79998889900", role="admin")
        u.set_password("1234")
        db.session.add(u)
        db.session.commit()
        print("  + admin@demo.ru / 1234")


def migrate_existing_tables():
    """Добавляет новые колонки в уже существующие таблицы (безопасно)."""
    with db.engine.connect() as conn:
        migrations = [
            "ALTER TABLE appointments ADD COLUMN service_id INT NULL",
            "ALTER TABLE appointments ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'scheduled'",
            "ALTER TABLE doctors ADD COLUMN photo VARCHAR(200) NULL",
            "ALTER TABLE users ADD COLUMN reset_token VARCHAR(64) NULL",
            "ALTER TABLE users ADD COLUMN reset_token_exp DATETIME NULL",
        ]
        for sql in migrations:
            try:
                conn.execute(db.text(sql))
                conn.commit()
                print(f"  + {sql[:60]}...")
            except Exception:
                pass  # колонка уже существует


if __name__ == "__main__":
    with app.app_context():
        print(" Создание таблиц...")
        db.create_all()

        print(" Миграция существующих таблиц...")
        migrate_existing_tables()

        print(" Сидер услуг...")
        seed_services()

        print(" Сидер ачивок...")
        seed_achievements()

        print(" Сидер кабинетов...")
        seed_offices()

        print(" Сидер демо-юзеров...")
        seed_demo_users()

        print("\n Готово! Теперь можно запускать app.py")


