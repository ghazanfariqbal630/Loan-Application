from flask import Flask, render_template, request, redirect, flash, session, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import os
from sqlalchemy import func, text
import secrets
import string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
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
    branch_code = db.Column(db.String(10), nullable=True)  # Changed to nullable for non-branch users
    branch_name = db.Column(db.String(100), nullable=True)  # Changed to nullable
    district = db.Column(db.String(50), nullable=True)  # Changed to nullable
    sub_region = db.Column(db.String(50), nullable=True)  # Changed to nullable
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    dashboard_access = db.Column(db.Boolean, default=True)
    user_type = db.Column(db.String(20), default='branch_user')  # 'admin', 'boss', 'branch_user'

# ---------------- Database Migration ----------------
def migrate_database():
    try:
        with app.app_context():
            # Check and add dashboard_access column
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='user' AND column_name='dashboard_access'
            """))
            
            if not result.fetchone():
                db.session.execute(text('ALTER TABLE "user" ADD COLUMN dashboard_access BOOLEAN DEFAULT TRUE'))
                print("✅ Added dashboard_access column")
            
            # Check and add user_type column
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='user' AND column_name='user_type'
            """))
            
            if not result.fetchone():
                db.session.execute(text('ALTER TABLE "user" ADD COLUMN user_type VARCHAR(20) DEFAULT \'branch_user\''))
                print("✅ Added user_type column")
                
            # Make branch columns nullable for non-branch users
            try:
                db.session.execute(text('ALTER TABLE "user" ALTER COLUMN branch_code DROP NOT NULL'))
                db.session.execute(text('ALTER TABLE "user" ALTER COLUMN branch_name DROP NOT NULL'))
                db.session.execute(text('ALTER TABLE "user" ALTER COLUMN district DROP NOT NULL'))
                db.session.execute(text('ALTER TABLE "user" ALTER COLUMN sub_region DROP NOT NULL'))
                print("✅ Made branch columns nullable")
            except:
                print("ℹ️ Branch columns already nullable")
                
            db.session.commit()
                
    except Exception as e:
        print(f"⚠️ Database migration note: {e}")

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
            session["is_boss"] = False
            session["user_type"] = "admin"
            session["dashboard_access"] = True
            flash("Admin login successful!", "success")
            return redirect("/dashboard")
        
        # Check other user credentials
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.password == password:
            session["logged_in"] = True
            session["username"] = user.username
            session["branch_code"] = user.branch_code
            session["branch_name"] = user.branch_name
            session["district"] = user.district
            session["sub_region"] = user.sub_region
            session["dashboard_access"] = user.dashboard_access
            session["user_type"] = user.user_type
            
            # Set permissions based on user type
            if user.user_type == 'admin':
                session["is_admin"] = True
                session["is_boss"] = False
            elif user.user_type == 'boss':
                session["is_admin"] = False
                session["is_boss"] = True
            else:  # branch_user
                session["is_admin"] = False
                session["is_boss"] = False
            
            flash(f"Welcome {user.username}!", "success")
            
            if session["dashboard_access"]:
                return redirect("/dashboard")
            else:
                return redirect("/")
        else:
            flash("Incorrect username or password!", "danger")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect("/")

# ---------------- User Management Routes (Admin Only) ----------------
@app.route("/manage_users")
def manage_users():
    if not session.get("logged_in") or not session.get("is_admin"):
        flash("Access denied! Admin access required.", "danger")
        return redirect("/dashboard")
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("manage_users.html", users=users, branches=branches)

@app.route("/create_user", methods=["POST"])
def create_user():
    if not session.get("logged_in") or not session.get("is_admin"):
        flash("Access denied! Admin access required.", "danger")
        return redirect("/dashboard")
    
    username = request.form.get("username")
    user_type = request.form.get("user_type", "branch_user")
    dashboard_access = 'dashboard_access' in request.form
    branch_code = request.form.get("branch_code")
    
    # Validate username
    if not username:
        flash("Username is required!", "danger")
        return redirect("/manage_users")
    
    # Check if username already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash("Username already exists! Please choose a different username.", "danger")
        return redirect("/manage_users")
    
    # Generate password
    password = generate_strong_password()
    
    # Create user based on type
    if user_type == 'branch_user':
        # Branch user - require branch selection
        if not branch_code:
            flash("Branch selection is required for branch users!", "danger")
            return redirect("/manage_users")
            
        branch = next((b for b in branches if b["code"] == branch_code), None)
        if not branch:
            flash("Invalid branch code!", "danger")
            return redirect("/manage_users")
        
        new_user = User(
            username=username,
            password=password,
            branch_code=branch["code"],
            branch_name=branch["name"],
            district=branch["district"],
            sub_region=branch["sub_region"],
            dashboard_access=dashboard_access,
            user_type=user_type
        )
    else:
        # Non-branch user (admin or boss) - no branch association
        new_user = User(
            username=username,
            password=password,
            branch_code=None,
            branch_name=None,
            district=None,
            sub_region=None,
            dashboard_access=dashboard_access,
            user_type=user_type
        )
    
    try:
        db.session.add(new_user)
        db.session.commit()
        user_type_display = "Admin" if user_type == "admin" else "BOSS" if user_type == "boss" else "Branch User"
        flash(f"User created successfully! Username: {username}, Password: {password}, Type: {user_type_display}", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating user: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/toggle_dashboard_access/<int:user_id>", methods=["POST"])
def toggle_dashboard_access(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        flash("Access denied! Admin access required.", "danger")
        return redirect("/dashboard")
    
    user = User.query.get_or_404(user_id)
    
    try:
        user.dashboard_access = not user.dashboard_access
        db.session.commit()
        status = "enabled" if user.dashboard_access else "disabled"
        flash(f"Dashboard access {status} for user {user.username}", "success")
    except Exception as e:
        flash(f"Error updating dashboard access: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/delete_user/<int:user_id>")
def delete_user(user_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        flash("Access denied! Admin access required.", "danger")
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
        flash("Access denied! Admin access required.", "danger")
        return redirect("/dashboard")
    
    user = User.query.get_or_404(user_id)
    new_password = generate_strong_password()
    user.password = new_password
    
    try:
        db.session.commit()
        flash(f"Password reset successfully! New Password: {new_password}", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error resetting password: {str(e)}", "danger")
    
    return redirect("/manage_users")

# ---------------- Observation Delete Route (Admin Only) ----------------
@app.route("/delete_observation/<int:obs_id>")
def delete_observation(obs_id):
    if not session.get("logged_in") or not session.get("is_admin"):
        flash("Access denied! Admin access required.", "danger")
        return redirect("/dashboard")
    
    observation = Observation.query.get_or_404(obs_id)
    try:
        db.session.delete(observation)
        db.session.commit()
        flash("Observation deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting observation: {str(e)}", "danger")
    
    return redirect("/dashboard")

# ---------------- Dashboard Route ----------------
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/login")
    
    if not session.get("is_admin") and not session.get("is_boss") and not session.get("dashboard_access", True):
        flash("Dashboard access is disabled for your account. You can only submit observations.", "warning")
        return redirect("/")
    
    search = request.args.get('search','')
    query = Observation.query
    
    # Branch users can only see their branch data
    if not session.get("is_admin") and not session.get("is_boss"):
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
    
    if not session.get("is_admin") and not session.get("is_boss"):
        today_obs_query = today_obs_query.filter(Observation.branch_code == session.get("branch_code"))
        total_obs_query = total_obs_query.filter(Observation.branch_code == session.get("branch_code"))
    
    today_obs = today_obs_query.filter(Observation.date==datetime.utcnow().date()).count()
    total_obs = total_obs_query.count()
    
    # Get district and sub-region counts (only for admin and boss)
    district_counts = []
    sub_region_counts = []
    
    if session.get("is_admin") or session.get("is_boss"):
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

# ---------------- Main Route ----------------
@app.route("/", methods=["GET", "POST"])
def main():
    if session.get("logged_in"):
        return form_actual()
    else:
        return render_template("form.html")

# ---------------- Actual Form Route ----------------
def form_actual():
    if request.method == "POST":
        if not session.get("is_admin") and not session.get("is_boss"):
            code = session.get("branch_code")
        else:
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
    
    return render_template("form_actual.html", branches=branches, datetime=datetime)

# ---------------- Download Route ----------------
@app.route("/download")
def download():
    if not session.get("logged_in"):
        return redirect("/login")
    
    if not session.get("is_admin") and not session.get("is_boss") and not session.get("dashboard_access", True):
        flash("Download access is disabled for your account.", "warning")
        return redirect("/")
    
    query = Observation.query
    
    if not session.get("is_admin") and not session.get("is_boss"):
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

# ---------------- Branch List ----------------
branches = [
    # ... (your existing branch list)
]

# Run migration and create tables
with app.app_context():
    migrate_database()
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
