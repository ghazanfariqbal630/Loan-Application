from flask import Flask, render_template, request, redirect, flash, session, send_file, jsonify
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
            return redirect("/")  # Redirect to main route after login
        
        # Check branch user credentials
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.password == password:
            session["logged_in"] = True
            session["username"] = user.username
            session["branch_code"] = user.branch_code
            session["branch_name"] = user.branch_name
            session["district"] = user.district
            session["sub_region"] = user.sub_region
            session["is_admin"] = False
            flash(f"Welcome {user.branch_name}!", "success")
            return redirect("/")  # Redirect to main route after login
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
        password=password,  # Store actual password for admin viewing
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
    user.password = new_password  # Store new password for admin viewing
    
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
    if not session.get("logged_in") or not session.get("is_admin"):
        flash("Access denied!", "danger")
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

# ---------------- Main Route (Smart Routing) ----------------
@app.route("/", methods=["GET", "POST"])
def main():
    # If user is logged in, show the actual form
    if session.get("logged_in"):
        return form_actual()
    else:
        # If not logged in, show login required page
        return render_template("form.html")

# ---------------- Actual Form Route (Protected) ----------------
def form_actual():
    # This function handles the actual form for logged-in users
    if request.method == "POST":
        # For branch users, use their branch code automatically
        if not session.get("is_admin"):
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
    
    # For GET requests, show the actual form to logged-in users
    return render_template("form_actual.html", branches=branches, datetime=datetime)

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

if __name__ == "__main__":
    app.run(debug=True)
