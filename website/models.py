from . import db
from flask_login import UserMixin
import enum
from datetime import date, timezone, datetime


class UserRole(enum.Enum):
    ADMIN = "Supervisor"      # full access: view + edit all student data
    MODERATOR = "Overseer"    # view-only access to all student data
    STUDENT = "User"          # view + edit only their own data


class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"


# Human-readable (French) labels used by the school registry export, mapped
# to/from the internal Gender enum. Used by the import script and anywhere
# we need to display or parse the "Genre" column.
GENDER_FR_LABELS = {
    Gender.MALE: "Masculin",
    Gender.FEMALE: "Féminin",
}
GENDER_FR_LOOKUP = {v: k for k, v in GENDER_FR_LABELS.items()}


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    sex = db.Column(db.Enum(Gender), nullable=False)
    max_occupancy = db.Column(db.Integer, nullable=False, default=1)

    # Legacy link (unused by the current UI, kept for compatibility with User.room_id)
    residents = db.relationship('User', backref='room', lazy=True)

    # Actual student roster for a room
    students = db.relationship('Students', backref='room', lazy=True, foreign_keys='Students.room_id')

    @property
    def occupant_count(self):
        return len(self.students) #type: ignore

    @property
    def is_full(self):
        return self.occupant_count >= self.max_occupancy


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    account_type = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=True)

    # One login account can be linked to one student profile record.
    student_profile = db.relationship(
        'Students', backref='account', uselist=False, foreign_keys='Students.user_id'
    )

    def __init__(self, email=None, password=None, first_name=None, last_name=None,
                 room_id=None, account_type=None):
        self.email = email
        self.password = password
        self.first_name = first_name
        self.last_name = last_name
        self.room_id = room_id
        self.account_type = account_type or UserRole.STUDENT

    def is_admin(self):
        return self.account_type == UserRole.ADMIN

    def is_moderator(self):
        return self.account_type == UserRole.MODERATOR

    def is_student(self):
        return self.account_type == UserRole.STUDENT


class StudentStatus(enum.Enum):
    ACTIVE = "active"          # Actif
    WITHDRAWN = "withdrawn"    # Abandonné
    INACTIVE = "inactive"      # temporarily inactive (not part of the registry export)
    GRADUATED = "graduated"    # not part of the registry export


# Human-readable (French) labels used by the school registry export's
# "Etat" column, mapped to/from the internal StudentStatus enum.
STATUS_FR_LABELS = {
    StudentStatus.ACTIVE: "Actif",
    StudentStatus.WITHDRAWN: "Abandonné",
    StudentStatus.INACTIVE: "Inactif",
    StudentStatus.GRADUATED: "Diplômé",
}
STATUS_FR_LOOKUP = {v: k for k, v in STATUS_FR_LABELS.items()}


class Students(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Links a student data record to the User account that owns it, so a
    # normal user can be scoped to only their own row.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=True)

    # --- Academic identifiers, as they appear in the official school
    # registry export (Niveau / Filière / Classe / Code Élève / CNE). ---
    niveau = db.Column(db.String(50), nullable=False)            # e.g. "Première Année"
    filiere = db.Column(db.String(50), nullable=False)           # e.g. "ECS", "MP"
    classe = db.Column(db.String(50), nullable=False)            # e.g. "1-ECS-1"
    student_code = db.Column(db.String(20), nullable=False)      # Code Élève
    cne = db.Column(db.String(20), nullable=False, unique=True)  # CNE (national student number)

    # --- Identity ---
    last_name = db.Column(db.String(100), nullable=False)        # Nom
    first_name = db.Column(db.String(100), nullable=False)       # Prénom
    sex = db.Column(db.Enum(Gender), nullable=False)              # Genre
    birth_date = db.Column(db.Date, nullable=False)               # Date Naiss.
    birth_place = db.Column(db.String(100))                      # Lieu Naiss.
    nationality = db.Column(db.String(50))                       # Nationalité
    national_id = db.Column(db.String(20))                       # No CNI

    # --- Contact ---
    email = db.Column(db.String(100), unique=True)
    home_phone = db.Column(db.String(20))                        # Tél. Domicile
    phone = db.Column(db.String(20))                             # GSM
    address = db.Column(db.Text)                                 # Adresse
    city = db.Column(db.String(100))                             # Ville

    status = db.Column(db.Enum(StudentStatus), nullable=False, default=StudentStatus.ACTIVE)  # Etat

    # --- Dormitory-specific fields (not part of the registry export) ---
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=True)
    dormitory_id = db.Column(db.Integer, nullable=True)
    check_in_date = db.Column(db.Date)
    check_out_date = db.Column(db.Date)
    emergency_contact = db.Column(db.String(100))
    emergency_phone = db.Column(db.String(20))
    photo = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    @property
    def name(self):
        """Full display name ("Prénom Nom"). Kept as a convenience property
        since so much of the UI just wants one string to show."""
        return f"{self.first_name} {self.last_name}"

    @property
    def level_and_section(self):
        """Convenience label combining Niveau/Filière/Classe, e.g.
        "1-ECS-1 · Première Année (ECS)"."""
        return f"{self.classe} — {self.niveau} ({self.filiere})"


class AbsenceNotice(db.Model):
    """A student-submitted notice declaring a day they'll be absent, with a
    reason, visible to Supervisors (Admin) and Overseers (Moderator)."""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())

    student = db.relationship(
        'Students', backref=db.backref('absence_notices', lazy=True, order_by='AbsenceNotice.date.desc()')
    )
