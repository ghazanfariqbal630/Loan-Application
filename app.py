from flask import Flask, render_template, request, redirect, flash, send_file, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# ✅ PostgreSQL Connection (Render Environment)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- Database Model ----------------
class LoanApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    cnic = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(250), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    purpose = db.Column(db.String(50), nullable=False)
    contact = db.Column(db.String(15), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.create_all()

# ---------------- Simple Login System ----------------
USERNAME = "admin"     # 👈 apna username yahan likhen
PASSWORD = "12345"     # 👈 apna password yahan likhen

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == USERNAME and password == PASSWORD:
            session["logged_in"] = True
            return redirect("/dashboard")
        else:
            flash("غلط یوزر نیم یا پاس ورڈ!", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    flash("آپ کامیابی سے لاگ آؤٹ ہو گئے ہیں۔", "info")
    return redirect("/login")

# ---------------- Routes ----------------
@app.route("/", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        try:
            new_app = LoanApplication(
                name=request.form['name'],
                cnic=request.form['cnic'],
                address=request.form['address'],
                amount=float(request.form['amount']),
                purpose=request.form['purpose'],
                contact=request.form['contact']
            )
            db.session.add(new_app)
            db.session.commit()
            flash("درخواست کامیابی سے جمع ہوگئی!", "success")
            return redirect("/")
        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect("/")
    return render_template("form.html")

# ---------------- Dashboard with Filters, Search, Chart ----------------
@app.route("/dashboard", methods=["GET"])
def dashboard():
    if not session.get("logged_in"):
        flash("براہ کرم لاگ ان کریں!", "warning")
        return redirect("/login")

    search = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    query = LoanApplication.query

    # 🔍 Search Filter
    if search:
        query = query.filter(
            (LoanApplication.name.ilike(f"%{search}%")) |
            (LoanApplication.cnic.ilike(f"%{search}%")) |
            (LoanApplication.purpose.ilike(f"%{search}%"))
        )

    # 📅 Date Filter
    if start_date and end_date:
        query = query.filter(LoanApplication.created_at.between(start_date, end_date))

    records = query.order_by(LoanApplication.created_at.desc()).all()

    total = len(records)
    total_amount = sum(r.amount for r in records) if records else 0
    avg_amount = total_amount / total if total > 0 else 0
    today_count = LoanApplication.query.filter(
        db.func.date(LoanApplication.created_at) == datetime.utcnow().date()
    ).count()

    # 📊 Purpose-wise Data for Chart
    purpose_data = db.session.query(
        LoanApplication.purpose, db.func.count(LoanApplication.id)
    ).group_by(LoanApplication.purpose).all()

    purpose_labels = [p[0] for p in purpose_data]
    purpose_counts = [p[1] for p in purpose_data]

    return render_template(
        "dashboard.html",
        records=records,
        total=total,
        total_amount=total_amount,
        avg_amount=avg_amount,
        today_count=today_count,
        purpose_labels=purpose_labels,
        purpose_counts=purpose_counts,
        search=search,
        start_date=start_date,
        end_date=end_date
    )

# ---------------- Download Excel ----------------
@app.route("/download")
def download_excel():
    if not session.get("logged_in"):
        flash("براہ کرم لاگ ان کریں!", "warning")
        return redirect("/login")

    records = LoanApplication.query.order_by(LoanApplication.created_at.desc()).all()
    if not records:
        flash("کوئی درخواست موجود نہیں!", "danger")
        return redirect("/dashboard")

    df = pd.DataFrame([{
        "ID": r.id,
        "Name": r.name,
        "CNIC": r.cnic,
        "Address": r.address,
        "Amount": r.amount,
        "Purpose": r.purpose,
        "Contact": r.contact,
        "Created At": r.created_at.strftime("%Y-%m-%d %I:%M %p")
    } for r in records])

    file_path = "loan_applications.xlsx"
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
