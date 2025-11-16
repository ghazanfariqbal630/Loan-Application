from flask import Flask, render_template, request, redirect, flash, session, send_file, jsonify
from datetime import datetime
import pandas as pd
import os
import secrets
import string
import json
from supabase import create_client, Client
import uuid
from collections import Counter

app = Flask(__name__)

# ---------------- Supabase Configuration ----------------
# Direct values use karen
SUPABASE_URL = "https://srpqxiivopwvdygidxpv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNycHF4aWl2b3B3dmR5Z2lkeHB2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjI5NjgxMzUsImV4cCI6MjA3ODU0NDEzNX0.FHV6yk9XMZBRkpUI8y4A7GP3hXE31Qn6rSoRwmuZCys"
FLASK_SECRET_KEY = "any_random_secret_key_123"

app.config['SECRET_KEY'] = FLASK_SECRET_KEY

print("🔧 Initializing Supabase client...")
print(f"URL: {SUPABASE_URL}")

# Supabase client initialize karen
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase client initialized successfully")
except Exception as e:
    print(f"❌ Supabase client initialization failed: {e}")
    raise e

# ---------------- Database Models (Supabase Tables) ----------------
def create_tables():
    """Supabase me tables create karein agar nahi hain to"""
    try:
        # Observations table check karein
        result = supabase.table("observations").select("*").limit(1).execute()
        print("✅ Observations table already exists")
    except Exception as e:
        print("⚠️ Observations table might not exist:", e)
    
    try:
        # Users table check karein
        result = supabase.table("users").select("*").limit(1).execute()
        print("✅ Users table already exists")
    except Exception as e:
        print("⚠️ Users table might not exist:", e)

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
            session["observation_access"] = True
            session["compliance_access"] = True
            flash("Admin login successful!", "success")
            return redirect("/dashboard")
        
        # Check other user credentials from Supabase
        try:
            result = supabase.table("users").select("*").eq("username", username).eq("is_active", True).execute()
            
            if result.data and len(result.data) > 0:
                user = result.data[0]
                if user["password"] == password:
                    session["logged_in"] = True
                    session["username"] = user["username"]
                    session["branch_code"] = user["branch_code"]
                    session["branch_name"] = user["branch_name"]
                    session["district"] = user["district"]
                    session["sub_region"] = user["sub_region"]
                    session["dashboard_access"] = user["dashboard_access"]
                    session["user_type"] = user["user_type"]
                    
                    # Set permissions based on user type
                    if user["user_type"] == 'admin':
                        session["is_admin"] = True
                        session["is_boss"] = False
                        # Admin has all permissions
                        session["can_manage_users"] = True
                        session["can_delete_observations"] = True
                        session["can_access_all_branches"] = True
                        session["custom_branches_access"] = True
                        session["observation_access"] = True
                        session["compliance_access"] = True
                    elif user["user_type"] == 'boss':
                        session["is_admin"] = False
                        session["is_boss"] = True
                        # BOSS user - use individual permissions
                        session["can_manage_users"] = user["can_manage_users"]
                        session["can_delete_observations"] = user["can_delete_observations"]
                        session["can_access_all_branches"] = user["can_access_all_branches"]
                        session["custom_branches_access"] = user["custom_branches_access"]
                        session["allowed_branches"] = user["allowed_branches"]
                        session["observation_access"] = user["observation_access"]
                        session["compliance_access"] = user["compliance_access"]
                    elif user["user_type"] == 'compliance':
                        session["is_admin"] = False
                        session["is_boss"] = False
                        # Compliance user - specific permissions
                        session["can_manage_users"] = user["can_manage_users"]
                        session["can_delete_observations"] = user["can_delete_observations"]
                        session["can_access_all_branches"] = user["can_access_all_branches"]
                        session["custom_branches_access"] = user["custom_branches_access"]
                        session["allowed_branches"] = user["allowed_branches"]
                        session["observation_access"] = user["observation_access"]
                        session["compliance_access"] = user["compliance_access"]
                    else:  # branch_user
                        session["is_admin"] = False
                        session["is_boss"] = False
                        # Branch users have limited permissions
                        session["can_manage_users"] = False
                        session["can_delete_observations"] = False
                        session["can_access_all_branches"] = False
                        session["custom_branches_access"] = False
                        session["observation_access"] = user["observation_access"]
                        session["compliance_access"] = user["compliance_access"]
                    
                    flash(f"Welcome {user['username']}!", "success")
                    
                    if session["dashboard_access"]:
                        return redirect("/dashboard")
                    else:
                        return redirect("/")
                else:
                    flash("Incorrect username or password!", "danger")
            else:
                flash("Incorrect username or password!", "danger")
                
        except Exception as e:
            flash(f"Login error: {str(e)}", "danger")
    
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
    
    try:
        result = supabase.table("users").select("*").order("created_at", desc=True).execute()
        users = result.data if result.data else []
        
        # Fix: Convert created_at strings to datetime objects for template
        for user in users:
            if user.get('created_at'):
                # Remove 'Z' and convert to datetime object
                dt_str = user['created_at'].replace('Z', '')
                user['created_at'] = datetime.fromisoformat(dt_str)
                
    except Exception as e:
        flash(f"Error loading users: {str(e)}", "danger")
        users = []
    
    return render_template("manage_users.html", users=users, branches=branches)

@app.route("/create_user", methods=["POST"])
def create_user():
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    username = request.form.get("username")
    user_type = request.form.get("user_type", "branch_user")
    branch_code = request.form.get("branch_code")
    
    # Get all permission values
    dashboard_access = request.form.get("dashboard_access") == 'true'
    can_manage_users = request.form.get("can_manage_users") == 'true'
    can_delete_observations = request.form.get("can_delete_observations") == 'true'
    can_access_all_branches = request.form.get("can_access_all_branches") == 'true'
    custom_branches_access = request.form.get("custom_branches_access") == 'true'
    observation_access = request.form.get("observation_access") == 'true'
    compliance_access = request.form.get("compliance_access") == 'true'
    allowed_branches = request.form.get("allowed_branches", "")
    
    # Validate username
    if not username:
        flash("Username is required!", "danger")
        return redirect("/manage_users")
    
    # Check if username already exists
    try:
        existing_user = supabase.table("users").select("username").eq("username", username).execute()
        if existing_user.data:
            flash("Username already exists! Please choose a different username.", "danger")
            return redirect("/manage_users")
    except Exception as e:
        flash(f"Error checking username: {str(e)}", "danger")
        return redirect("/manage_users")
    
    # Generate password
    password = generate_strong_password()
    
    # Prepare user data
    user_data = {
        "username": username,
        "password": password,
        "dashboard_access": dashboard_access,
        "user_type": user_type,
        "can_manage_users": can_manage_users,
        "can_delete_observations": can_delete_observations,
        "can_access_all_branches": can_access_all_branches,
        "custom_branches_access": custom_branches_access,
        "observation_access": observation_access,
        "compliance_access": compliance_access,
        "allowed_branches": allowed_branches,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Add branch info for branch users
    if user_type == 'branch_user':
        if not branch_code:
            flash("Branch selection is required for branch users!", "danger")
            return redirect("/manage_users")
            
        branch = next((b for b in branches if b["code"] == branch_code), None)
        if not branch:
            flash("Invalid branch code!", "danger")
            return redirect("/manage_users")
        
        user_data.update({
            "branch_code": branch["code"],
            "branch_name": branch["name"],
            "district": branch["district"],
            "sub_region": branch["sub_region"]
        })
    
    try:
        result = supabase.table("users").insert(user_data).execute()
        user_type_display = "Admin" if user_type == "admin" else "BOSS" if user_type == "boss" else "Compliance" if user_type == "compliance" else "Branch User"
        flash(f"User created successfully! Username: {username}, Password: {password}, Type: {user_type_display}", "success")
    except Exception as e:
        flash(f"Error creating user: {str(e)}", "danger")
    
    return redirect("/manage_users")

# Permission toggle routes
@app.route("/toggle_dashboard_access/<user_id>", methods=["POST"])
def toggle_dashboard_access(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    try:
        # Get current value
        result = supabase.table("users").select("dashboard_access").eq("id", user_id).execute()
        if result.data:
            current_value = result.data[0]["dashboard_access"]
            new_value = not current_value
            
            # Update value
            supabase.table("users").update({"dashboard_access": new_value}).eq("id", user_id).execute()
            
            status = "enabled" if new_value else "disabled"
            flash(f"Dashboard access {status}", "success")
    except Exception as e:
        flash(f"Error updating dashboard access: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/toggle_manage_users/<user_id>", methods=["POST"])
def toggle_manage_users(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    try:
        result = supabase.table("users").select("can_manage_users").eq("id", user_id).execute()
        if result.data:
            current_value = result.data[0]["can_manage_users"]
            supabase.table("users").update({"can_manage_users": not current_value}).eq("id", user_id).execute()
            status = "enabled" if not current_value else "disabled"
            flash(f"User management access {status}", "success")
    except Exception as e:
        flash(f"Error updating user management access: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/toggle_delete_observations/<user_id>", methods=["POST"])
def toggle_delete_observations(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    try:
        result = supabase.table("users").select("can_delete_observations").eq("id", user_id).execute()
        if result.data:
            current_value = result.data[0]["can_delete_observations"]
            supabase.table("users").update({"can_delete_observations": not current_value}).eq("id", user_id).execute()
            status = "enabled" if not current_value else "disabled"
            flash(f"Observation delete access {status}", "success")
    except Exception as e:
        flash(f"Error updating observation delete access: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/toggle_all_branches_access/<user_id>", methods=["POST"])
def toggle_all_branches_access(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    try:
        result = supabase.table("users").select("can_access_all_branches").eq("id", user_id).execute()
        if result.data:
            current_value = result.data[0]["can_access_all_branches"]
            supabase.table("users").update({"can_access_all_branches": not current_value}).eq("id", user_id).execute()
            status = "enabled" if not current_value else "disabled"
            flash(f"All branches access {status}", "success")
    except Exception as e:
        flash(f"Error updating all branches access: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/toggle_custom_branches_access/<user_id>", methods=["POST"])
def toggle_custom_branches_access(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    try:
        result = supabase.table("users").select("custom_branches_access").eq("id", user_id).execute()
        if result.data:
            current_value = result.data[0]["custom_branches_access"]
            supabase.table("users").update({"custom_branches_access": not current_value}).eq("id", user_id).execute()
            status = "enabled" if not current_value else "disabled"
            flash(f"Custom branches access {status}", "success")
    except Exception as e:
        flash(f"Error updating custom branches access: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/toggle_observation_access/<user_id>", methods=["POST"])
def toggle_observation_access(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    try:
        result = supabase.table("users").select("observation_access").eq("id", user_id).execute()
        if result.data:
            current_value = result.data[0]["observation_access"]
            supabase.table("users").update({"observation_access": not current_value}).eq("id", user_id).execute()
            status = "enabled" if not current_value else "disabled"
            flash(f"Observation access {status}", "success")
    except Exception as e:
        flash(f"Error updating observation access: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/toggle_compliance_access/<user_id>", methods=["POST"])
def toggle_compliance_access(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    try:
        result = supabase.table("users").select("compliance_access").eq("id", user_id).execute()
        if result.data:
            current_value = result.data[0]["compliance_access"]
            supabase.table("users").update({"compliance_access": not current_value}).eq("id", user_id).execute()
            status = "enabled" if not current_value else "disabled"
            flash(f"Compliance access {status}", "success")
    except Exception as e:
        flash(f"Error updating compliance access: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/delete_user/<user_id>")
def delete_user(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    try:
        supabase.table("users").delete().eq("id", user_id).execute()
        flash("User deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting user: {str(e)}", "danger")
    
    return redirect("/manage_users")

@app.route("/reset_password/<user_id>")
def reset_password(user_id):
    if not session.get("logged_in") or not session.get("can_manage_users"):
        flash("Access denied! User management access required.", "danger")
        return redirect("/dashboard")
    
    new_password = generate_strong_password()
    
    try:
        supabase.table("users").update({"password": new_password}).eq("id", user_id).execute()
        flash(f"Password reset successfully! New Password: {new_password}", "success")
    except Exception as e:
        flash(f"Error resetting password: {str(e)}", "danger")
    
    return redirect("/manage_users")

# ---------------- Observation Delete Route ----------------
@app.route("/delete_observation/<observation_id>")
def delete_observation(observation_id):
    if not session.get("logged_in") or not session.get("can_delete_observations"):
        flash("Access denied! Observation delete access required.", "danger")
        return redirect("/dashboard")
    
    try:
        supabase.table("observations").delete().eq("id", observation_id).execute()
        flash("Observation deleted successfully!", "success")
    except Exception as e:
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
    
    try:
        # Build query based on access permissions
        query = supabase.table("observations").select("*")
        
        # Check access permissions
        if session.get("is_admin") or session.get("can_access_all_branches"):
            # Admin or user with all branches access - can see all data
            pass
        elif session.get("custom_branches_access") and session.get("allowed_branches"):
            # User with custom branches access
            allowed_branches_list = session.get("allowed_branches", "").split(",")
            query = query.in_("branch_code", allowed_branches_list)
        else:
            # Branch user or limited access - can only see their branch data
            query = query.eq("branch_code", session.get("branch_code"))
        
        # Apply search filter
        if search:
            # Note: Supabase doesn't support ILIKE directly in Python client, so we'll filter after
            result = query.execute()
            records = result.data if result.data else []
            # Manual search filter
            records = [r for r in records if (
                search.lower() in r.get('customer_name', '').lower() or
                search.lower() in r.get('cnic', '').lower() or
                search.lower() in r.get('client_observation', '').lower() or
                search.lower() in r.get('branch_name', '').lower() or
                search.lower() in r.get('district', '').lower() or
                search.lower() in r.get('sub_region', '').lower()
            )]
        else:
            result = query.order("date", desc=True).execute()
            records = result.data if result.data else []
        
        # Fix: Convert created_at strings to datetime objects for dashboard
        for record in records:
            if record.get('created_at'):
                dt_str = record['created_at'].replace('Z', '')
                record['created_at'] = datetime.fromisoformat(dt_str)
        
        # Calculate statistics
        today = datetime.utcnow().date().isoformat()
        
        today_obs_query = supabase.table("observations").select("id", count="exact").eq("date", today)
        total_obs_query = supabase.table("observations").select("id", count="exact")
        
        # Apply access filters to statistics
        if not (session.get("is_admin") or session.get("can_access_all_branches")):
            if session.get("custom_branches_access") and session.get("allowed_branches"):
                allowed_branches_list = session.get("allowed_branches", "").split(",")
                today_obs_query = today_obs_query.in_("branch_code", allowed_branches_list)
                total_obs_query = total_obs_query.in_("branch_code", allowed_branches_list)
            else:
                today_obs_query = today_obs_query.eq("branch_code", session.get("branch_code"))
                total_obs_query = total_obs_query.eq("branch_code", session.get("branch_code"))
        
        today_obs_result = today_obs_query.execute()
        total_obs_result = total_obs_query.execute()
        
        today_obs = len(today_obs_result.data) if today_obs_result.data else 0
        total_obs = len(total_obs_result.data) if total_obs_result.data else 0
        
        # Get district and sub-region counts
        district_counts = []
        sub_region_counts = []
        
        if session.get("is_admin") or session.get("can_access_all_branches"):
            district_result = supabase.table("observations").select("district").execute()
            sub_region_result = supabase.table("observations").select("sub_region").execute()
        elif session.get("custom_branches_access") and session.get("allowed_branches"):
            allowed_branches_list = session.get("allowed_branches", "").split(",")
            district_result = supabase.table("observations").select("district").in_("branch_code", allowed_branches_list).execute()
            sub_region_result = supabase.table("observations").select("sub_region").in_("branch_code", allowed_branches_list).execute()
        else:
            district_result = supabase.table("observations").select("district").eq("branch_code", session.get("branch_code")).execute()
            sub_region_result = supabase.table("observations").select("sub_region").eq("branch_code", session.get("branch_code")).execute()
        
        # Manual counting for districts
        if district_result.data:
            district_counts = Counter([r['district'] for r in district_result.data if r['district']]).items()
        
        # Manual counting for sub-regions
        if sub_region_result.data:
            sub_region_counts = Counter([r['sub_region'] for r in sub_region_result.data if r['sub_region']]).items()
        
    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "danger")
        records = []
        today_obs = 0
        total_obs = 0
        district_counts = []
        sub_region_counts = []
    
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
        
        # Prepare observation data for Supabase
        observation_data = {
            "date": request.form['date'],
            "branch_code": branch["code"],
            "branch_name": branch["name"],
            "district": branch["district"],
            "sub_region": branch["sub_region"],
            "customer_name": request.form['customer_name'],
            "cnic": request.form['cnic'],
            "client_observation": request.form['client_observation'],
            "feedback": '',
            "shared_with": request.form.get('shared_with',''),
            "remarks": '',
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            result = supabase.table("observations").insert(observation_data).execute()
            flash("Observation saved successfully!", "success")
        except Exception as e:
            flash(f"Error saving observation: {str(e)}", "danger")
        
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
    
    try:
        query = supabase.table("observations").select("*")
        
        # Check access permissions for download
        if session.get("is_admin") or session.get("can_access_all_branches"):
            # Can download all data
            pass
        elif session.get("custom_branches_access") and session.get("allowed_branches"):
            allowed_branches_list = session.get("allowed_branches", "").split(",")
            query = query.in_("branch_code", allowed_branches_list)
        else:
            query = query.eq("branch_code", session.get("branch_code"))
        
        result = query.order("date", desc=True).execute()
        records = result.data if result.data else []
        
        df = pd.DataFrame([{
            "Date": r["date"],
            "Branch Code": r["branch_code"],
            "Branch Name": r["branch_name"],
            "District": r["district"],
            "Sub Region": r["sub_region"],
            "Customer Name": r["customer_name"],
            "CNIC": r["cnic"],
            "Observation": r["client_observation"],
            "Shared With": r["shared_with"]
        } for r in records])
        
        file_path = "observations.xlsx"
        df.to_excel(file_path, index=False)
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        flash(f"Error downloading data: {str(e)}", "danger")
        return redirect("/dashboard")

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

# Initialize tables on startup
with app.app_context():
    create_tables()

if __name__ == "__main__":
    app.run(debug=True)
