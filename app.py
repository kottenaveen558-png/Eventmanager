from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = \
    "mysql+pymysql://root:912153@localhost:3306/student_manager"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "replace-with-a-secure-key")

db = SQLAlchemy(app)

SUPER_ADMIN_USERNAME = os.getenv("SUPER_ADMIN_USERNAME", "superadmin")
SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "superadmin123")


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


class StaffRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    phone = db.Column(db.String(50), nullable=False, unique=True)
    department = db.Column(db.String(150), nullable=True)
    created_at = db.Column(db.String(100), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    phone = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.String(100), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class PendingAdminRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    requested_at = db.Column(db.String(100), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    status = db.Column(db.String(20), nullable=False, default="pending")


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

        if username == SUPER_ADMIN_USERNAME and password == SUPER_ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            session["is_super_admin"] = True
            session["admin_username"] = username
            return redirect(url_for("admin_dashboard"))

        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            session["admin_logged_in"] = True
            session["is_super_admin"] = False
            session["admin_username"] = username
            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin credentials.", "danger")

    return render_template("admin_login.html")

@app.route("/admin")
def admin_portal():
    return render_template("admin_portal.html")


@app.route("/admin/signup", methods=["GET", "POST"])
def admin_signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        phone = request.form.get("phone", "").strip()

        if not email or not username or not password or not phone:
            flash("Please fill in all fields.", "danger")
            return render_template("admin_signup.html")

        if Admin.query.filter((Admin.username == username) | (Admin.email == email)).first():
            flash("This username or email is already registered.", "danger")
            return render_template("admin_signup.html")

        if PendingAdminRequest.query.filter(
            (PendingAdminRequest.username == username) | (PendingAdminRequest.email == email)
        ).first():
            flash("A request for this username or email already exists.", "warning")
            return render_template("admin_signup.html")

        staff_record = StaffRecord.query.filter(
            (StaffRecord.email == email) | (StaffRecord.phone == phone)
        ).first()

        if not staff_record:
            flash("Your details were not found in the staff database.", "danger")
            return render_template("admin_signup.html")

        pending_request = PendingAdminRequest(
            username=username,
            email=email,
            phone=phone,
            password_hash=generate_password_hash(password),
            status="pending"
        )
        db.session.add(pending_request)
        db.session.commit()

        flash("Your admin request has been submitted for approval.", "success")
        return redirect(url_for("admin_login"))

    return render_template("admin_signup.html")
@app.route("/superadmin/login", methods=["GET", "POST"])

def superadmin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == SUPER_ADMIN_USERNAME and password == SUPER_ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            session["is_super_admin"] = True
            session["admin_username"] = username
            flash("Welcome Super Admin!", "success")
            return redirect(url_for("admin_dashboard"))

        flash("Invalid Super Admin credentials.", "danger")

    return render_template("superadmin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("is_super_admin", None)
    session.pop("admin_username", None)
    flash("Logged out successfully.", "success")
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    events = Event.query.order_by(Event.date.asc()).all()
    pending_count = PendingAdminRequest.query.filter_by(status="pending").count()
    return render_template(
        "admin_dashboard.html",
        events=events,
        pending_count=pending_count,
        is_super_admin=session.get("is_super_admin", False)
    )


@app.route("/admin/pending-requests")
def pending_admin_requests():
    if not session.get("admin_logged_in") or not session.get("is_super_admin"):
        return redirect(url_for("admin_login"))

    requests = PendingAdminRequest.query.order_by(PendingAdminRequest.requested_at.desc()).all()
    return render_template("pending_admin_requests.html", requests=requests)


@app.route("/admin/requests/<int:request_id>/approve")
def approve_admin_request(request_id):
    if not session.get("admin_logged_in") or not session.get("is_super_admin"):
        return redirect(url_for("admin_login"))

    request_record = PendingAdminRequest.query.get_or_404(request_id)

    approved_admin = Admin(
        username=request_record.username,
        email=request_record.email,
        phone=request_record.phone,
        password_hash=request_record.password_hash
    )
    db.session.add(approved_admin)
    db.session.delete(request_record)
    db.session.commit()

    flash("Admin request approved.", "success")
    return redirect(url_for("pending_admin_requests"))


@app.route("/admin/requests/<int:request_id>/reject")
def reject_admin_request(request_id):
    if not session.get("admin_logged_in") or not session.get("is_super_admin"):
        return redirect(url_for("admin_login"))

    request_record = PendingAdminRequest.query.get_or_404(request_id)
    db.session.delete(request_record)
    db.session.commit()

    flash("Admin request rejected.", "success")
    return redirect(url_for("pending_admin_requests"))


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
        try:
            db.session.execute(text("SELECT 1"))
            print("Database connection successful")
        except Exception as e:
            print(f"Database connection failed: {e}")
        db.create_all()
    app.run(debug=True)
