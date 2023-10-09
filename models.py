##dont forget to install pip install Flask-SQLAlchemy

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)

    # Relationships (if you need to query the related records directly from an employee instance)
    availabilities = db.relationship('Availability', backref='employee')
    work_logs = db.relationship('WorkLog', backref='employee')
    time_off_requests = db.relationship('TimeOffRequest', backref='employee')


class Availability(db.Model):
    __tablename__ = 'availability'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    day = db.Column(db.String, nullable=False)
    start_time = db.Column(db.String, nullable=False)
    end_time = db.Column(db.String, nullable=False)
    notes = db.Column(db.String)
    submission_time = db.Column(db.String, nullable=False)  # You might want to change this to a DateTime field


class WorkLog(db.Model):
    __tablename__ = 'work_logs'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'))
    date = db.Column(db.String, nullable=False)
    start_time = db.Column(db.String, nullable=False)
    end_time = db.Column(db.String, nullable=False)
    hours_worked = db.Column(db.Float)
    tips_earned = db.Column(db.Float)
    location = db.Column(db.String, nullable=False)


class TimeOffRequest(db.Model):
    __tablename__ = 'request_time_off'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    name = db.Column(db.String, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String)
