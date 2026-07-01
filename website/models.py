from . import db
from flask_login import UserMixin
import enum
from datetime import date, timezone, datetime


class UserRole(enum.Enum):
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    STUDENT = "student"

class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20))
    sex = db.Column(db.Enum(Gender), nullable=False)
    residents = db.relationship('User', backref='room', lazy=True)
    room_number = db.Column(db.String(3))



class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    account_type = db.Column(db.Enum(UserRole), nullable = False)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    
    def __init__(self, email=None, password=None, first_name=None, last_name=None, room_id=None):
        self.email = email
        self.password = password
        self.first_name = first_name
        self.last_name = last_name
        self.room_id = room_id

class StudentStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    GRADUATED = "graduated"

class Students(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
