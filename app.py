from flask import Flask, render_template, request, redirect, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import os
from sqlalchemy import func
import secrets
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")  # PostgreSQL URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------- Database Models ----------------
class Observation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow)
    branch_code = db.Column(db.String(10), nullable=False)
    branch_name = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    sub_region = db.Column(db.String(50), nullable=False)
    customer_name = db.Column(db.String(150), nullable=False)
    cnic = db.Column(db.String(15), nullable=False)
    client_observation = db.Column(db.Text, nullable=False)
    feedback = db.Column(db.Text)
    shared_with = db.Column(db.String(50))
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    branch_code = db.Column(db.String(10), nullable=False)
    branch_name = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    sub_region = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

with app.app_context():
    db.create_all()

# ---------------- Password Generator ----------------
def generate_strong_password(length=8):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# ---------------- Login System ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Check admin credentials first
        if username == "admin" and password == "nrsp1234":
            session["logged_in"] = True
            session["username"] = "admin"
            session["is_admin"] = True
            flash("Admin login successful!", "success")
            return redirect("/dashboard")
        
        # Check branch user credentials
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.password == password:  # In production, use proper password hashing
            session["logged_in"] = True
            session["username"] = user.username
            session["branch_code"] = user.branch_code
            session["branch_name"] = user.branch_name
            session["is_admin"] = False
            flash(f"Welcome {user.branch_name}!", "success")
            return redirect("/dashboard")
        else:
            flash("Incorrect username or password!", "danger")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect("/login")

# ---------------- User Management Routes ----------------
@app.route("/manage_users")
def manage_users():
    if not session.get("logged_in") or not session.get("is_admin"):
        flash("Access denied!", "danger")
        return redirect("/dashboard")
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("manage_users.html", users=users, branches=branches)

@app.route("/create_user", methods=["POST"])
def create_user():
    if not session.get("logged_in") or not session.get("is_admin"):
        flash("Access denied!", "danger")
        return redirect("/dashboard")
    
    branch_code = request.form.get("branch_code")
    branch = next((b for b in branches if b["code"] == branch_code), None)
    
    if not branch:
        flash("Invalid branch code!", "danger")
        return redirect("/manage_users")
    
    # Generate username (branch code + random digits)
    base_username = branch_code
    username = base_username
    counter = 1
    
    # Ensure unique username
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1
    
    # Generate password
    password = generate_strong_password()
    
    # Create user
    new_user = User(
        username=username,
        password=password,  # In production, hash this password
        branch_code=branch["code"],
        branch_name=branch["name"],
        district=branch["district"],
        sub_region=branch["sub_region"]
    )
    
    try:
        db.session.add(new_user)
        db.session.commit()
        flash(f"User created successfully! Username: {username}, Password: {password}", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating user: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/delete_user/<int:user_id>")
def delete_user(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        flash("Access denied!", "danger")
        return redirect("/dashboard")
    
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting user: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/reset_password/<int:user_id>")
def reset_password(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        flash("Access denied!", "danger")
        return redirect("/dashboard")
    
    user = User.query.get_or_404(user_id)
    new_password = generate_strong_password()
    user.password = new_password  # In production, hash this password
    
    try:
        db.session.commit()
        flash(f"Password reset successfully! New Password: {new_password}", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error resetting password: {str(e)}", "danger")
    
    return redirect("/manage_users")

# ---------------- Updated Dashboard Route ----------------
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/login")
    
    search = request.args.get('search','')
    query = Observation.query
    
    # Branch users can only see their branch data
    if not session.get("is_admin"):
        query = query.filter(Observation.branch_code == session.get("branch_code"))
    
    if search:
        query = query.filter(
            (Observation.customer_name.ilike(f"%{search}%")) |
            (Observation.cnic.ilike(f"%{search}%")) |
            (Observation.client_observation.ilike(f"%{search}%")) |
            (Observation.branch_name.ilike(f"%{search}%")) |
            (Observation.district.ilike(f"%{search}%")) |
            (Observation.sub_region.ilike(f"%{search}%"))
        )
    
    records = query.order_by(Observation.date.desc()).all()
    
    # Calculate statistics
    today_obs_query = Observation.query
    total_obs_query = Observation.query
    
    if not session.get("is_admin"):
        today_obs_query = today_obs_query.filter(Observation.branch_code == session.get("branch_code"))
        total_obs_query = total_obs_query.filter(Observation.branch_code == session.get("branch_code"))
    
    today_obs = today_obs_query.filter(Observation.date==datetime.utcnow().date()).count()
    total_obs = total_obs_query.count()
    
    # Get district and sub-region counts (only for admin)
    district_counts = []
    sub_region_counts = []
    
    if session.get("is_admin"):
        district_counts = db.session.query(
            Observation.district, 
            func.count(Observation.id)
        ).group_by(Observation.district).all()
        
        sub_region_counts = db.session.query(
            Observation.sub_region, 
            func.count(Observation.id)
        ).group_by(Observation.sub_region).all()
    
    return render_template("dashboard.html", 
                         records=records, 
                         today_obs=today_obs, 
                         total_obs=total_obs,
                         district_counts=district_counts,
                         sub_region_counts=sub_region_counts,
                         search=search)

# ---------------- Updated Form Route ----------------
@app.route("/", methods=["GET","POST"])
def form():
    if request.method == "POST":
        code = request.form['branch_code']
        branch = next((b for b in branches if b["code"] == code), None)
        if not branch:
            flash("Invalid Branch Code", "danger")
            return redirect("/")
        obs = Observation(
            date=request.form['date'],
            branch_code=branch["code"],
            branch_name=branch["name"],
            district=branch["district"],
            sub_region=branch["sub_region"],
            customer_name=request.form['customer_name'],
            cnic=request.form['cnic'],
            client_observation=request.form['client_observation'],
            feedback='',
            shared_with=request.form.get('shared_with',''),
            remarks=''
        )
        db.session.add(obs)
        db.session.commit()
        flash("Observation saved successfully!", "success")
        return redirect("/")
    return render_template("form.html", branches=branches, datetime=datetime)

# ---------------- Updated Download Route ----------------
@app.route("/download")
def download():
    if not session.get("logged_in"):
        return redirect("/login")
    
    query = Observation.query
    
    # Branch users can only download their branch data
    if not session.get("is_admin"):
        query = query.filter(Observation.branch_code == session.get("branch_code"))
    
    query = query.order_by(Observation.date.desc()).all()
    
    df = pd.DataFrame([{
        "Date": r.date,
        "Branch Code": r.branch_code,
        "Branch Name": r.branch_name,
        "District": r.district,
        "Sub Region": r.sub_region,
        "Customer Name": r.customer_name,
        "CNIC": r.cnic,
        "Observation": r.client_observation,
        "Shared With": r.shared_with
    } for r in query])
    
    file_path = "observations.xlsx"
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

# ... (keep the existing branches list and other code the same)
