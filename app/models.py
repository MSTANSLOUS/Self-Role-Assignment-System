from flask_sqlalchemy import SQLAlchemy

db =SQLAlchemy()

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(80))
    description = db.Column(db.String(500))
    spots = db.Column(db.Integer)  # Added this to hold the number of available spots!

    # NEW: This helps the Role know which Users belong to it
    users = db.relationship('User', backref='role', lazy=True)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    email = db.Column(db.String(120))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))