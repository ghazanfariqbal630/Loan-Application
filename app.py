from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
import pandas as pd
import random
import string
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change this to a strong secret key

# PostgreSQL Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@hostname:port/dbname'  # Replace with your Render PostgreSQL URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ----------------- Database Models -----------------

class Branch(db.Model):
    __tablename__ = "branches"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(50))
    sub_region = db.Column(db.String(50))
    password = db.Column(db.String(200))  # Hashed password
    active = db.Column(db.Boolean, default=True)

class Observation(db.Model):
    __tablename__ = "observations"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow)
    branch_code = db.Column(db.String(10), nullable=False)
    branch_name = db.Column(db.String(100))
    district = db.Column(db.String(50))
    sub_region = db.Column(db.String(50))
    customer_name = db.Column(db.String(100))
    cnic = db.Column(db.String(20))
    client_observation = db.Column(db.String(500))
    shared_with = db.Column(db.String(100))

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))  # Hashed password
    role = db.Column(db.String(20))  # admin or branch

# ----------------- Helper Functions -----------------

def generate_password(length=8):
    """Generate random password"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def branch_dict():
    branches = Branch.query.all()
    return [
        {"code": b.code, "name": b.name, "district": b.district, "sub_region": b.sub_region}
        for b in branches
    ]

# ----------------- Routes -----------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return redirect(url_for("dashboard") if user.role=="admin" else url_for("form_page"))
        else:
            flash("Invalid username or password", "danger")
            return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -------- Admin Dashboard --------
@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "role" not in session or session["role"] != "admin":
        flash("Access Denied", "danger")
        return redirect(url_for("login"))
    
    search = request.args.get("search", "")
    query = Observation.query
    if search:
        query = query.filter(
            Observation.customer_name.ilike(f"%{search}%") |
            Observation.cnic.ilike(f"%{search}%") |
            Observation.branch_name.ilike(f"%{search}%") |
            Observation.district.ilike(f"%{search}%")
        )
    records = query.order_by(Observation.date.desc()).all()
    
    today_obs = Observation.query.filter_by(date=datetime.utcnow().date()).count()
    total_obs = Observation.query.count()
    
    # District-wise and subregion-wise counts
    district_counts = db.session.query(Observation.district, db.func.count(Observation.id)).group_by(Observation.district).all()
    sub_region_counts = db.session.query(Observation.sub_region, db.func.count(Observation.id)).group_by(Observation.sub_region).all()
    
    return render_template(
        "dashboard.html",
        records=records,
        today_obs=today_obs,
        total_obs=total_obs,
        district_counts=district_counts,
        sub_region_counts=sub_region_counts,
        search=search
    )

# -------- Excel Download --------
@app.route("/download")
def download_excel():
    if "role" not in session or session["role"] != "admin":
        flash("Access Denied", "danger")
        return redirect(url_for("login"))
    
    records = Observation.query.all()
    data = [{
        "Date": r.date,
        "Branch Code": r.branch_code,
        "Branch Name": r.branch_name,
        "District": r.district,
        "Sub Region": r.sub_region,
        "Customer Name": r.customer_name,
        "CNIC": r.cnic,
        "Client Observation": r.client_observation,
        "Shared With": r.shared_with
    } for r in records]
    
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    
    return send_file(output, download_name="observations.xlsx", as_attachment=True)

# -------- Branch User Form --------
@app.route("/form", methods=["GET", "POST"])
def form_page():
    if "role" not in session or session["role"] != "branch":
        flash("Access Denied", "danger")
        return redirect(url_for("login"))
    
    branches_list = branch_dict()
    
    if request.method == "POST":
        obs = Observation(
            date = request.form["date"],
            branch_code = request.form["branch_code"],
            branch_name = request.form["branch_name"],
            district = request.form["district"],
            sub_region = request.form["sub_region"],
            customer_name = request.form["customer_name"],
            cnic = request.form["cnic"],
            client_observation = request.form["client_observation"],
            shared_with = request.form.get("shared_with", "")
        )
        db.session.add(obs)
        db.session.commit()
        flash("Observation Saved Successfully", "success")
        return redirect(url_for("form_page"))
    
    return render_template("form.html", branches=branches_list)

# -------- Admin - Branch Password Generate --------
@app.route("/generate_password/<int:branch_id>")
def generate_branch_password(branch_id):
    if "role" not in session or session["role"] != "admin":
        flash("Access Denied", "danger")
        return redirect(url_for("login"))
    
    branch = Branch.query.get_or_404(branch_id)
    if branch.password:
        flash("Password already generated for this branch", "info")
    else:
        new_password = generate_password()
        branch.password = generate_password_hash(new_password)
        db.session.commit()
        flash(f"Password generated for {branch.name}: {new_password}", "success")
    return redirect(url_for("dashboard"))

# -------- Admin - Enable/Disable Branch --------
@app.route("/toggle_branch/<int:branch_id>")
def toggle_branch(branch_id):
    if "role" not in session or session["role"] != "admin":
        flash("Access Denied", "danger")
        return redirect(url_for("login"))
    
    branch = Branch.query.get_or_404(branch_id)
    branch.active = not branch.active
    db.session.commit()
    status = "enabled" if branch.active else "disabled"
    flash(f"Branch {branch.name} is now {status}", "success")
    return redirect(url_for("dashboard"))

# ----------------- Run App -----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
