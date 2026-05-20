from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///events.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "replace-with-a-secure-key"

db = SQLAlchemy(app)

ADMIN_USERNAME = "Naveen kotte"
ADMIN_PASSWORD = "Naveen143@"

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    venue = db.Column(db.String(150), nullable=False)
    organizer = db.Column(db.String(150), nullable=False)
    seats = db.Column(db.Integer, nullable=False)

    registrations = db.relationship("Registration", backref="event", cascade="all, delete-orphan")

    def remaining_seats(self):
        return self.seats - len(self.registrations)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    roll_number = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)

    registrations = db.relationship("Registration", backref="student", cascade="all, delete-orphan")

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    registered_at = db.Column(db.String(100), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route("/")
def home():
    return render_template("landing.html", body_class="landing")

@app.route("/student")
def student():
    events = Event.query.order_by(Event.date.asc()).all()
    return render_template("events.html", events=events)

@app.route("/register/<int:event_id>", methods=["GET", "POST"])
def register(event_id):
    event = Event.query.get_or_404(event_id)

    if event.remaining_seats() <= 0:
        flash("This event is full. Please choose another event.", "warning")
        return redirect(url_for("student"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll_number = request.form.get("roll_number", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name or not roll_number or not email or not phone:
            flash("Please fill in all registration fields.", "danger")
            return render_template("register.html", event=event)

        student = Student(name=name, roll_number=roll_number, email=email, phone=phone)
        db.session.add(student)
        db.session.commit()

        registration = Registration(student_id=student.id, event_id=event.id)
        db.session.add(registration)
        db.session.commit()

        flash(f"Thank you, {name}! You are registered for {event.name}.", "success")
        return redirect(url_for("student"))

    return render_template("register.html", event=event)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin credentials.", "danger")

    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("admin_login"))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    events = Event.query.order_by(Event.date.asc()).all()
    return render_template("admin_dashboard.html", events=events)

@app.route("/admin/events/add", methods=["GET", "POST"])
def add_event():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        date = request.form.get("date", "").strip()
        time = request.form.get("time", "").strip()
        venue = request.form.get("venue", "").strip()
        organizer = request.form.get("organizer", "").strip()
        seats = request.form.get("seats", "0").strip()

        if not name or not date or not time or not venue or not organizer or not seats:
            flash("Please complete all event fields.", "danger")
            return render_template("add_event.html")

        try:
            seats_value = int(seats)
        except ValueError:
            flash("Seats must be a valid number.", "danger")
            return render_template("add_event.html")

        event = Event(name=name, date=date, time=time, venue=venue, organizer=organizer, seats=seats_value)
        db.session.add(event)
        db.session.commit()

        flash("Event created successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_event.html")

@app.route("/admin/events/edit/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    event = Event.query.get_or_404(event_id)

    if request.method == "POST":
        event.name = request.form.get("name", event.name).strip()
        event.date = request.form.get("date", event.date).strip()
        event.time = request.form.get("time", event.time).strip()
        event.venue = request.form.get("venue", event.venue).strip()
        event.organizer = request.form.get("organizer", event.organizer).strip()
        seats = request.form.get("seats", str(event.seats)).strip()

        if not event.name or not event.date or not event.time or not event.venue or not event.organizer or not seats:
            flash("Please complete all event fields.", "danger")
            return render_template("edit_event.html", event=event)

        try:
            event.seats = int(seats)
        except ValueError:
            flash("Seats must be a valid number.", "danger")
            return render_template("edit_event.html", event=event)

        db.session.commit()
        flash("Event updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_event.html", event=event)

@app.route("/admin/events/delete/<int:event_id>")
def delete_event(event_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()

    flash("Event deleted successfully.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/registrations")
def view_registrations():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    registrations = Registration.query.order_by(Registration.registered_at.desc()).all()
    return render_template("view_registrations.html", registrations=registrations)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
