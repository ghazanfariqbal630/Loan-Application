from flask import Flask, render_template, request, redirect, flash, session, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import os
from sqlalchemy import func, text
import secrets
import string
import json

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
    branch_code = db.Column(db.String(10), nullable=True)
    branch_name = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(50), nullable=True)
    sub_region = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    dashboard_access = db.Column(db.Boolean, default=True)
    user_type = db.Column(db.String(20), default='branch_user')
    
    # NEW: Permission fields for BOSS and Admin users
    can_manage_users = db.Column(db.Boolean, default=False)
    can_delete_observations = db.Column(db.Boolean, default=False)
    can_access_all_branches = db.Column(db.Boolean, default=False)
    custom_branches_access = db.Column(db.Boolean, default=False)
    allowed_branches = db.Column(db.Text, nullable=True)  # JSON string of branch codes

# ---------------- Database Migration ----------------
def migrate_database():
    try:
        with app.app_context():
            # Check and add new columns
            columns_to_add = [
                ('dashboard_access', 'BOOLEAN DEFAULT TRUE'),
                ('user_type', 'VARCHAR(20) DEFAULT \'branch_user\''),
                ('can_manage_users', 'BOOLEAN DEFAULT FALSE'),
                ('can_delete_observations', 'BOOLEAN DEFAULT FALSE'),
                ('can_access_all_branches', 'BOOLEAN DEFAULT FALSE'),
                ('custom_branches_access', 'BOOLEAN DEFAULT FALSE'),
                ('allowed_branches', 'TEXT')
            ]
            
            for column_name, column_type in columns_to_add:
                result = db.session.execute(text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='user' AND column_name='{column_name}'
                """))
                
                if not result.fetchone():
                    db.session.execute(text(f'ALTER TABLE "user" ADD COLUMN {column_name} {column_type}'))
                    print(f"✅ Added {column_name} column")
            
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
            # Admin has all permissions
            session["can_manage_users"] = True
            session["can_delete_observations"] = True
            session["can_access_all_branches"] = True
            session["custom_branches_access"] = True
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
                # Admin has all permissions
                session["can_manage_users"] = True
                session["can_delete_observations"] = True
                session["can_access_all_branches"] = True
                session["custom_branches_access"] = True
            elif user.user_type == 'boss':
                session["is_admin"] = False
                session["is_boss"] = True
                # BOSS user - use individual permissions
                session["can_manage_users"] = user.can_manage_users
                session["can_delete_observations"] = user.can_delete_observations
                session["can_access_all_branches"] = user.can_access_all_branches
                session["custom_branches_access"] = user.custom_branches_access
                session["allowed_branches"] = user.allowed_branches
            else:  # branch_user
                session["is_admin"] = False
                session["is_boss"] = False
                # Branch users have limited permissions
                session["can_manage_users"] = False
                session["can_delete_observations"] = False
                session["can_access_all_branches"] = False
                session["custom_branches_access"] = False
            
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

# ---------------- User Management Routes ----------------
@app.route("/manage_users")
def manage_users():
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("manage_users.html", users=users, branches=branches)

@app.route("/create_user", methods=["POST"])
def create_user():
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    username = request.form.get("username")
    user_type = request.form.get("user_type", "branch_user")
    dashboard_access = 'dashboard_access' in request.form
    branch_code = request.form.get("branch_code")
    
    # NEW: Permissions for BOSS and Admin users
    can_manage_users = 'can_manage_users' in request.form
    can_delete_observations = 'can_delete_observations' in request.form
    can_access_all_branches = 'can_access_all_branches' in request.form
    custom_branches_access = 'custom_branches_access' in request.form
    allowed_branches = request.form.get("allowed_branches", "")
    
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
            user_type=user_type,
            # Branch users have limited permissions
            can_manage_users=False,
            can_delete_observations=False,
            can_access_all_branches=False,
            custom_branches_access=False
        )
    else:
        # Non-branch user (admin or boss)
        new_user = User(
            username=username,
            password=password,
            branch_code=None,
            branch_name=None,
            district=None,
            sub_region=None,
            dashboard_access=dashboard_access,
            user_type=user_type,
            # Set permissions for BOSS/Admin users
            can_manage_users=can_manage_users if user_type == 'boss' else True,
            can_delete_observations=can_delete_observations if user_type == 'boss' else True,
            can_access_all_branches=can_access_all_branches if user_type == 'boss' else True,
            custom_branches_access=custom_branches_access if user_type == 'boss' else True,
            allowed_branches=allowed_branches if user_type == 'boss' else None
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
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
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

# NEW: Toggle permission routes
@app.route("/toggle_manage_users/<int:user_id>", methods=["POST"])
def toggle_manage_users(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    user = User.query.get_or_404(user_id)
    
    try:
        user.can_manage_users = not user.can_manage_users
        db.session.commit()
        status = "enabled" if user.can_manage_users else "disabled"
        flash(f"User management access {status} for user {user.username}", "success")
    except Exception as e:
        flash(f"Error updating user management access: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/toggle_delete_observations/<int:user_id>", methods=["POST"])
def toggle_delete_observations(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    user = User.query.get_or_404(user_id)
    
    try:
        user.can_delete_observations = not user.can_delete_observations
        db.session.commit()
        status = "enabled" if user.can_delete_observations else "disabled"
        flash(f"Observation delete access {status} for user {user.username}", "success")
    except Exception as e:
        flash(f"Error updating observation delete access: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/toggle_all_branches_access/<int:user_id>", methods=["POST"])
def toggle_all_branches_access(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    user = User.query.get_or_404(user_id)
    
    try:
        user.can_access_all_branches = not user.can_access_all_branches
        db.session.commit()
        status = "enabled" if user.can_access_all_branches else "disabled"
        flash(f"All branches access {status} for user {user.username}", "success")
    except Exception as e:
        flash(f"Error updating all branches access: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/toggle_custom_branches_access/<int:user_id>", methods=["POST"])
def toggle_custom_branches_access(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    user = User.query.get_or_404(user_id)
    
    try:
        user.custom_branches_access = not user.custom_branches_access
        db.session.commit()
        status = "enabled" if user.custom_branches_access else "disabled"
        flash(f"Custom branches access {status} for user {user.username}", "success")
    except Exception as e:
        flash(f"Error updating custom branches access: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/delete_user/<int:user_id>")
def delete_user(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
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
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
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

# ---------------- Observation Delete Route ----------------
@app.route("/delete_observation/<int:obs_id>")
def delete_observation(obs_id):
    if not session.get("logged_in") or not session.get("can_delete_observations"):
        flash("Access denied! Observation delete access required.", "danger")
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
    
    # Check access permissions
    if session.get("is_admin") or session.get("can_access_all_branches"):
        # Admin or user with all branches access - can see all data
        pass
    elif session.get("custom_branches_access") and session.get("allowed_branches"):
        # User with custom branches access
        allowed_branches_list = session.get("allowed_branches", "").split(",")
        query = query.filter(Observation.branch_code.in_(allowed_branches_list))
    else:
        # Branch user or limited access - can only see their branch data
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
    
    # Calculate statistics based on access
    today_obs_query = Observation.query
    total_obs_query = Observation.query
    
    if session.get("is_admin") or session.get("can_access_all_branches"):
        # Can see all statistics
        pass
    elif session.get("custom_branches_access") and session.get("allowed_branches"):
        allowed_branches_list = session.get("allowed_branches", "").split(",")
        today_obs_query = today_obs_query.filter(Observation.branch_code.in_(allowed_branches_list))
        total_obs_query = total_obs_query.filter(Observation.branch_code.in_(allowed_branches_list))
    else:
        today_obs_query = today_obs_query.filter(Observation.branch_code == session.get("branch_code"))
        total_obs_query = total_obs_query.filter(Observation.branch_code == session.get("branch_code"))
    
    today_obs = today_obs_query.filter(Observation.date==datetime.utcnow().date()).count()
    total_obs = total_obs_query.count()
    
    # Get district and sub-region counts based on access
    district_counts = []
    sub_region_counts = []
    
    if session.get("is_admin") or session.get("can_access_all_branches"):
        district_counts = db.session.query(
            Observation.district, 
            func.count(Observation.id)
        ).group_by(Observation.district).all()
        
        sub_region_counts = db.session.query(
            Observation.sub_region, 
            func.count(Observation.id)
        ).group_by(Observation.sub_region).all()
    elif session.get("custom_branches_access") and session.get("allowed_branches"):
        allowed_branches_list = session.get("allowed_branches", "").split(",")
        district_counts = db.session.query(
            Observation.district, 
            func.count(Observation.id)
        ).filter(Observation.branch_code.in_(allowed_branches_list)).group_by(Observation.district).all()
        
        sub_region_counts = db.session.query(
            Observation.sub_region, 
            func.count(Observation.id)
        ).filter(Observation.branch_code.in_(allowed_branches_list)).group_by(Observation.sub_region).all()
    
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
    
    # Check access permissions for download
    if session.get("is_admin") or session.get("can_access_all_branches"):
        # Can download all data
        pass
    elif session.get("custom_branches_access") and session.get("allowed_branches"):
        allowed_branches_list = session.get("allowed_branches", "").split(",")
        query = query.filter(Observation.branch_code.in_(allowed_branches_list))
    else:
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
    {"code":"0012","name":"ISA KHAIL-FU-MLI","district":"Mianwali","sub_region":"Mianwali"},
    {"code":"0014","name":"KALA BAGH-FU-MLI","district":"Mianwali","sub_region":"Mianwali"},
    {"code":"0594","name":"Kundian-FU-MLI","district":"Mianwali","sub_region":"Mianwali"},
    {"code":"0010","name":"MIANWALI-FU-MLI","district":"Mianwali","sub_region":"Mianwali"},
    {"code":"0593","name":"Moch-FU-MLI","district":"Mianwali","sub_region":"Mianwali"},
    {"code":"0013","name":"PIPLAN-FU-MLI","district":"Mianwali","sub_region":"Mianwali"},
    {"code":"0016","name":"JAUHARABAD-FU-KHB","district":"Khushab","sub_region":"Mianwali"},
    {"code":"0094","name":"QUAIDABAD-FU-KHB","district":"Khushab","sub_region":"Mianwali"},
    {"code":"0591","name":"Khushab-FU-KHB","district":"Khushab","sub_region":"Mianwali"},
    {"code":"0592","name":"Mitha Tawana-FU-KHB","district":"Khushab","sub_region":"Mianwali"},
    {"code":"0017","name":"NOORPUR THAL-FU-KHB","district":"Khushab","sub_region":"Mianwali"},
    {"code":"0093","name":"NOWSHEHRA-FU-KHB","district":"Khushab","sub_region":"Mianwali"},
    {"code":"0746","name":"GIROT-FU-KHB","district":"Khushab","sub_region":"Mianwali"},
    {"code":"0147","name":"BHAKKAR-FU-BHK","district":"Bhakkar","sub_region":"Mianwali"},
    {"code":"0150","name":"DULLEWALA-FU-BHK","district":"Bhakkar","sub_region":"Mianwali"},
    {"code":"0153","name":"KALURKOT-FU-BHK","district":"Bhakkar","sub_region":"Mianwali"},
    {"code":"0154","name":"MANKERA-FU-BHK","district":"Bhakkar","sub_region":"Mianwali"},
    {"code":"0588","name":"BHAKKAR-II-FU-BHK","district":"Bhakkar","sub_region":"Mianwali"},
    {"code":"0589","name":"Hyderabad Thal-FU-BHK","district":"Bhakkar","sub_region":"Mianwali"},
    {"code":"0092","name":"KOTMOMIN-FU-SGD","district":"Sargodha-B","sub_region":"Sargodha"},
    {"code":"0095","name":"SAHIWAL-FU-SGD","district":"Sargodha-A","sub_region":"Sargodha"},
    {"code":"0096","name":"SARGODHA-FU-SGD","district":"Sargodha-A","sub_region":"Sargodha"},
    {"code":"0097","name":"SHAHPUR SADAR-FU-SGD","district":"Sargodha-B","sub_region":"Sargodha"},
    {"code":"0333","name":"BHALWAL-FU-SGD","district":"Sargodha-B","sub_region":"Sargodha"},
    {"code":"0334","name":"SILANWALI-FU-SGD","district":"Sargodha-A","sub_region":"Sargodha"},
    {"code":"0358","name":"BHERA-FU-SGD","district":"Sargodha-B","sub_region":"Sargodha"},
    {"code":"0595","name":"Bhagtan Wala-FU-SGD","district":"Sargodha-A","sub_region":"Sargodha"},
    {"code":"0596","name":"Haiderabad Town-FU-SGD","district":"Sargodha-A","sub_region":"Sargodha"},
    {"code":"0597","name":"111 SB-FU-SGD","district":"Sargodha-A","sub_region":"Sargodha"},
    {"code":"0645","name":"SIAL_MORE-FU-SGD","district":"Sargodha-B","sub_region":"Sargodha"},
    {"code":"0646","name":"JHAVRIAN-FU-SGD","district":"Sargodha-B","sub_region":"Sargodha"},
    {"code":"0360","name":"PINDI BHATTIAN-FU-HFZ","district":"Hafizabad","sub_region":"Sargodha"},
    {"code":"0361","name":"JALALPUR BHATTIAN-FU-HFZ","district":"Hafizabad","sub_region":"Sargodha"},
    {"code":"0365","name":"HAFIZABAD-FU-HFZ","district":"Hafizabad","sub_region":"Sargodha"},
    {"code":"0644","name":"SUKHEKI_MINDI-FU-HFZ","district":"Hafizabad","sub_region":"Sargodha"},
    {"code":"0744","name":"VANEKI TARAR-FU HFZ","district":"Hafizabad","sub_region":"Sargodha"},
    {"code":"0701","name":"HAFIZABAD-FU-APC","district":"Hafizabad","sub_region":"Sargodha"},
    {"code":"0390","name":"GUJRAWAL-FU-GJW","district":"Wazirabad","sub_region":"Gujranwala"},
    {"code":"0391","name":"WAZIRABAD-FU-GJW","district":"Wazirabad","sub_region":"Gujranwala"},
    {"code":"0394","name":"ALI PUR CHATTA-FU-GJW","district":"Wazirabad","sub_region":"Gujranwala"},
    {"code":"0693","name":"Qila Didar Singh-FU-GJW","district":"Gujranwala","sub_region":"Gujranwala"},
    {"code":"0392","name":"NOSHERA VIRKAN-FU-GJW","district":"Gujranwala","sub_region":"Gujranwala"},
    {"code":"0393","name":"KAMOKE-FU-GJW","district":"Gujranwala","sub_region":"Gujranwala"},
    {"code":"0590","name":"Gujranwala-II-FU-GJW","district":"Gujranwala","sub_region":"Gujranwala"},
    {"code":"0761","name":"Gujranwala-Rural-FU-GJW","district":"Gujranwala","sub_region":"Gujranwala"},
    {"code":"0362","name":"CHINIOT-FU-CNT","district":"Chiniot","sub_region":"Sargodha"},
    {"code":"0363","name":"LALIAN-FU-CNT","district":"Chiniot","sub_region":"Sargodha"},
    {"code":"0364","name":"BAWANA-FU-CNT","district":"Chiniot","sub_region":"Sargodha"},
    {"code":"0745","name":"JAMIA ABAD-FU-CNT","district":"Chiniot","sub_region":"Sargodha"},
    {"code":"0558","name":"Narowal-FU-NRL","district":"Narowal","sub_region":"Gujranwala"},
    {"code":"0747","name":"Narowal-II-FU-NRL","district":"Narowal","sub_region":"Gujranwala"},
    {"code":"0560","name":"Shakar Garh-FU-NRL","district":"Narowal","sub_region":"Gujranwala"},
    {"code":"0679","name":"Shakar Garh-II-FU-NRL","district":"Narowal","sub_region":"Gujranwala"},
    {"code":"0559","name":"Zafarwal-FU-NRL","district":"Narowal","sub_region":"Gujranwala"},
    {"code":"0552","name":"Sialkot-FU-SKT","district":"Sialkot-B","sub_region":"Gujranwala"},
    {"code":"0555","name":"Pasrur-FU-SKT","district":"Sialkot-A","sub_region":"Gujranwala"},
    {"code":"0553","name":"Daska-FU-SKT","district":"Sialkot-A","sub_region":"Gujranwala"},
    {"code":"0554","name":"Sambrial-FU-SKT","district":"Wazirabad","sub_region":"Gujranwala"},
    {"code":"0748","name":"MOTRA-FU-SKT","district":"Sialkot-A","sub_region":"Gujranwala"},
    {"code":"0678","name":"WADALA-FU-SKT","district":"Sialkot-A","sub_region":"Gujranwala"},
    {"code":"0737","name":"KOTLI LOHARAN-FU-SKT","district":"Sialkot-B","sub_region":"Gujranwala"},
    {"code":"0608","name":"JHANG-FU-JHG","district":"Jhang-A","sub_region":"Faisalabad"},
    {"code":"0609","name":"ATHARA_HAZARI-FU-JHG","district":"Jhang-A","sub_region":"Faisalabad"},
    {"code":"0610","name":"SHORKOT-FU-JHG","district":"Jhang-B","sub_region":"Faisalabad"},
    {"code":"0611","name":"AHMED_PUR_SIAL-FU-JHG","district":"Jhang-B","sub_region":"Faisalabad"},
    {"code":"0702","name":"JHANG-II-FU-JHG","district":"Jhang-A","sub_region":"Faisalabad"},
    {"code":"0756","name":"WARIAMWALA-FU-JHG","district":"Jhang-B","sub_region":"Faisalabad"},
    {"code":"0824","name":"AKRIANWALA-FU-JNG","district":"Jhang-A","sub_region":"Faisalabad"},
    {"code":"0825","name":"KOT SHAKIR-FU-JNG","district":"Jhang-A","sub_region":"Faisalabad"},
    {"code":"0614","name":"FAISALABAD-II-FU-FSD","district":"Faisalabad-A","sub_region":"Faisalabad"},
    {"code":"0615","name":"CHAK_JHUMRA-FU-FSD","district":"Faisalabad-B","sub_region":"Faisalabad"},
    {"code":"0616","name":"JARANWALA-FU-FSD","district":"Faisalabad-B","sub_region":"Faisalabad"},
    {"code":"0617","name":"SAMUNDRI-FU-FSD","district":"Faisalabad-A","sub_region":"Faisalabad"},
    {"code":"0618","name":"TANDLIANWALA-FU-FSD","district":"Faisalabad-B","sub_region":"Faisalabad"},
    {"code":"0613","name":"FAISALABAD-I-FU-FSD","district":"Faisalabad-A","sub_region":"Faisalabad"},
    {"code":"0760","name":"NARWALA-FU-FSD","district":"Faisalabad-A","sub_region":"Faisalabad"},
    {"code":"0758","name":"KHURIANWALA-FU-FSD","district":"Faisalabad-B","sub_region":"Faisalabad"},
    {"code":"0759","name":"KHIDERWALA-FU-FSD","district":"Faisalabad-A","sub_region":"Faisalabad"},
    {"code":"0822","name":"SATYANA -FU-FSD","district":"Faisalabad-B","sub_region":"Faisalabad"},
    {"code":"0620","name":"KAMALIA-FU-TTS","district":"Toba Tek Singh","sub_region":"Faisalabad"},
    {"code":"0621","name":"GOJRA-FU-TTS","district":"Toba Tek Singh","sub_region":"Faisalabad"},
    {"code":"0622","name":"TOBA TEK SINGH-FU-TTS","district":"Toba Tek Singh","sub_region":"Faisalabad"},
    {"code":"0630","name":"PIR MEHAL-FU-TTS","district":"Toba Tek Singh","sub_region":"Faisalabad"},
    {"code":"0826","name":"MONGI BANGLA-FU-TTS","district":"Toba Tek Singh","sub_region":"Faisalabad"},
    {"code":"0827","name":"SANDHLIAN WALI-FU-TTS","district":"Toba Tek Singh","sub_region":"Faisalabad"},
    {"code":"0624","name":"OKARHA-FU-OKA","district":"Okara","sub_region":"Sahiwal"},
    {"code":"0667","name":"RENALAKHURD-FU-SWL","district":"Okara","sub_region":"Sahiwal"},
    {"code":"0666","name":"DEPALPUR-FU-SWL","district":"Okara","sub_region":"Sahiwal"},
    {"code":"0767","name":"GHAMBER-FU-OKA","district":"Okara","sub_region":"Sahiwal"},
    {"code":"0628","name":"SAHIWAL-FU-SWL","district":"Sahiwal","sub_region":"Sahiwal"},
    {"code":"0629","name":"CHICHAWATNI-FU-SWL","district":"Sahiwal","sub_region":"Sahiwal"},
    {"code":"0765","name":"KAMEER-FU-SWL","district":"Sahiwal","sub_region":"Sahiwal"},
    {"code":"0766","name":"HARAPA-FU-SWL","district":"Sahiwal","sub_region":"Sahiwal"},
    {"code":"0634","name":"Pakpattan-FU-LHR","district":"Pakpatan","sub_region":"Sahiwal"},
    {"code":"0643","name":"ARIFWALA-FU-SWL","district":"Pakpatan","sub_region":"Sahiwal"},
    {"code":"0763","name":"NOORPUR-FU-PPT","district":"Pakpatan","sub_region":"Sahiwal"},
    {"code":"0764","name":"QUBULA-FU-PPT","district":"Pakpatan","sub_region":"Sahiwal"}
]

# Run migration and create tables
with app.app_context():
    migrate_database()
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
