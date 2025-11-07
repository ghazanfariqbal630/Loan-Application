from flask import Flask, render_template, request, redirect, flash, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")  # PostgreSQL URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------- Database Model ----------------
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

with app.app_context():
    db.create_all()

# ---------------- Simple Login ----------------
USERNAME = "admin"
PASSWORD = "nrsp1234"  # Changed password

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == USERNAME and password == PASSWORD:
            session["logged_in"] = True
            return redirect("/dashboard")
        else:
            flash("Incorrect username or password!", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    flash("You have been logged out successfully.", "info")
    return redirect("/login")

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


# ---------------- Routes ----------------
@app.route("/", methods=["GET","POST"])
def form():
    if not session.get("logged_in"):
        return redirect("/login")
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
            feedback=request.form.get('feedback',''),
            shared_with=request.form.get('shared_with',''),
            remarks=request.form.get('remarks','')
        )
        db.session.add(obs)
        db.session.commit()
        flash("Observation saved successfully!", "success")  # English message
        return redirect("/")
    return render_template("form.html", branches=branches, datetime=datetime)

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/login")
    search = request.args.get('search','')
    query = Observation.query
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
    today_obs = Observation.query.filter(Observation.date==datetime.utcnow().date()).count()
    total_obs = Observation.query.count()
    return render_template("dashboard.html", records=records, today_obs=today_obs, total_obs=total_obs, search=search)

@app.route("/download")
def download():
    if not session.get("logged_in"):
        return redirect("/login")
    query = Observation.query.order_by(Observation.date.desc()).all()
    df = pd.DataFrame([{
        "Date": r.date,
        "Branch Code": r.branch_code,
        "Branch Name": r.branch_name,
        "District": r.district,
        "Sub Region": r.sub_region,
        "Customer Name": r.customer_name,
        "CNIC": r.cnic,
        "Observation": r.client_observation,
        "Feedback": r.feedback,
        "Shared With": r.shared_with,
        "Remarks": r.remarks
    } for r in query])
    file_path = "observations.xlsx"
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
