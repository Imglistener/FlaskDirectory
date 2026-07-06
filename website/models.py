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
    # BUG FIX: this column was being set in __init__ but never declared,
    # which raised an AttributeError/UnmappedColumnError as soon as a
    # room_id was passed in.
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
    ACTIVE = "active"
    INACTIVE = "inactive"
    GRADUATED = "graduated"


class Students(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Links a student data record to the User account that owns it, so a
    # normal user can be scoped to only their own row.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=True)
    name = db.Column(db.String(100), nullable=False)
    student_code = db.Column(db.String(20), nullable=False)
    internal_number = db.Column(db.String(20), nullable=False)
    level_and_section = db.Column(db.String(50), nullable=False)
    national_id = db.Column(db.String(20), nullable=False)
    sex = db.Column(db.Enum(Gender), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    status = db.Column(db.Enum(StudentStatus), nullable=False, default=StudentStatus.ACTIVE)
    address = db.Column(db.Text)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=True)
    dormitory_id = db.Column(db.Integer, nullable=True)
    check_in_date = db.Column(db.Date)
    check_out_date = db.Column(db.Date)
    emergency_contact = db.Column(db.String(100))
    emergency_phone = db.Column(db.String(20))
    nationality = db.Column(db.String(50))
    home_town = db.Column(db.String(100))
    photo = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
