from flask import Flask, render_template, request, redirect, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
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

@app.route("/dashboard")
def dashboard():
    records = LoanApplication.query.order_by(LoanApplication.created_at.desc()).all()
    total = len(records)
    total_amount = sum(r.amount for r in records) if records else 0
    avg_amount = total_amount / total if total > 0 else 0
    today_count = LoanApplication.query.filter(
        db.func.date(LoanApplication.created_at) == datetime.utcnow().date()
    ).count()
    return render_template("dashboard.html", records=records, total=total,
                           total_amount=total_amount, avg_amount=avg_amount, today_count=today_count)

@app.route("/download")
def download_excel():
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
