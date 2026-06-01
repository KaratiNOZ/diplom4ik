"""
ORM-модели SQLAlchemy для АИС стоматологической клиники.
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id_user = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="patient")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(64), nullable=True)
    reset_token_exp = db.Column(db.DateTime, nullable=True)

    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id_patient"), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id_doctor"), nullable=True)

    patient = db.relationship("Patient", backref=db.backref("user", uselist=False))
    doctor = db.relationship("Doctor", backref=db.backref("user", uselist=False))

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def role_label(self) -> str:
        labels = {
            "patient": "Пациент",
            "doctor":  f"Врач — {self.doctor.qualification}" if self.doctor else "Врач",
            "manager": "Менеджер",
            "admin":   "Администратор",
        }
        return labels.get(self.role, self.role)

    @property
    def first_name(self):
        if self.patient: return self.patient.first_name
        if self.doctor:  return self.doctor.first_name
        return self.email.split("@")[0]

    @property
    def last_name(self):
        if self.patient: return self.patient.last_name
        if self.doctor:  return self.doctor.last_name
        return ""

    @property
    def middle_name(self):
        if self.patient: return self.patient.middle_name
        if self.doctor:  return self.doctor.middle_name
        return ""

    def __repr__(self):
        return f"<User {self.id_user} {self.email} ({self.role})>"


class Doctor(db.Model):
    __tablename__ = "doctors"

    id_doctor = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(50))
    middle_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    qualification = db.Column(db.String(100))
    experience = db.Column(db.Integer)
    photo = db.Column(db.String(200), nullable=True)  # имя файла в images/doctors/

    appointments = db.relationship("Appointment", back_populates="doctor")
    histories = db.relationship("MedicalHistory", back_populates="doctor")

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(p for p in parts if p)

    def __repr__(self):
        return f"<Doctor {self.id_doctor} {self.full_name}>"


class Patient(db.Model):
    __tablename__ = "patients"

    id_patient = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(50))
    middle_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(30))
    birth_date = db.Column(db.Date)

    appointments = db.relationship("Appointment", back_populates="patient")
    histories = db.relationship("MedicalHistory", back_populates="patient")

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(p for p in parts if p)

    def __repr__(self):
        return f"<Patient {self.id_patient} {self.full_name}>"


class Office(db.Model):
    __tablename__ = "offices"

    id_office = db.Column(db.Integer, primary_key=True, autoincrement=True)
    office_number = db.Column(db.Integer)

    appointments = db.relationship("Appointment", back_populates="office")

    def __repr__(self):
        return f"<Office #{self.office_number}>"


class Service(db.Model):
    """Справочник услуг клиники."""
    __tablename__ = "services"

    id_service = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Numeric(10, 2))
    category = db.Column(db.String(80))

    appointments = db.relationship("Appointment", back_populates="service")

    def __repr__(self):
        return f"<Service {self.name}>"


class Appointment(db.Model):
    __tablename__ = "appointments"

    id_appointment = db.Column(db.Integer, primary_key=True, autoincrement=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id_doctor"))
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id_patient"))
    office_id = db.Column(db.Integer, db.ForeignKey("offices.id_office"))
    service_id = db.Column(db.Integer, db.ForeignKey("services.id_service"), nullable=True)
    appointment_date = db.Column(db.Date)
    appointment_time = db.Column(db.Time)
    status = db.Column(db.String(20), default="scheduled")
    # scheduled | completed | cancelled

    doctor = db.relationship("Doctor", back_populates="appointments")
    patient = db.relationship("Patient", back_populates="appointments")
    office = db.relationship("Office", back_populates="appointments")
    service = db.relationship("Service", back_populates="appointments")

    def __repr__(self):
        return f"<Appointment {self.id_appointment} {self.appointment_date}>"


class MedicalHistory(db.Model):
    __tablename__ = "medical_history"

    id_history = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id_patient"))
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id_doctor"))
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    visit_date = db.Column(db.Date)

    patient = db.relationship("Patient", back_populates="histories")
    doctor = db.relationship("Doctor", back_populates="histories")

    def __repr__(self):
        return f"<History {self.id_history} patient={self.patient_id} {self.visit_date}>"


class Achievement(db.Model):
    __tablename__ = "achievements"

    id_achievement = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    icon = db.Column(db.String(50), default="i-trophy")
    total = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f"<Achievement {self.code}>"


class PatientAchievement(db.Model):
    __tablename__ = "patient_achievements"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id_patient"), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey("achievements.id_achievement"), nullable=False)
    progress = db.Column(db.Integer, default=0)
    unlocked_at = db.Column(db.DateTime, nullable=True)

    patient = db.relationship("Patient", backref="achievement_progress")
    achievement = db.relationship("Achievement")

    __table_args__ = (
        db.UniqueConstraint("patient_id", "achievement_id", name="uq_patient_achievement"),
    )

    @property
    def unlocked(self) -> bool:
        return self.unlocked_at is not None

    def __repr__(self):
        return f"<PatientAch p={self.patient_id} a={self.achievement_id} {self.progress}>"
