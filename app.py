# app.py
from flask import Flask, render_template, request, redirect, send_file, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime, date
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = "secret-key"  # Flash messages کے لیے ضروری
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///loans.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- Models ----------------
class LoanApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    cnic = db.Column(db.String(15), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    amount = db.Column(db.Numeric(12,2), nullable=False)
    purpose = db.Column(db.String(200), nullable=True)
    contact = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------------- Routes ----------------
@app.before_first_request
def create_tables():
    db.create_all()

@app.route("/")
def index():
    total = db.session.query(func.count(LoanApplication.id)).scalar() or 0
    total_amount = db.session.query(func.coalesce(func.sum(LoanApplication.amount),0)).scalar()
    avg_amount = db.session.query(func.coalesce(func.avg(LoanApplication.amount),0)).scalar()
    today_count = db.session.query(func.count(LoanApplication.id))\
        .filter(func.date(LoanApplication.created_at) == date.today()).scalar()

    records = LoanApplication.query.order_by(LoanApplication.created_at.desc()).all()
    return render_template("dashboard.html",
                           total=total,
                           total_amount=total_amount,
                           avg_amount=avg_amount,
                           today_count=today_count,
                           records=records)

@app.route("/add", methods=["GET", "POST"])
def add_loan():
    if request.method == "POST":
        try:
            loan = LoanApplication(
                name=request.form['name'],
                cnic=request.form['cnic'],
                address=request.form.get('address'),
                amount=float(request.form['amount']),
                purpose=request.form.get('purpose'),
                contact=request.form.get('contact')
            )
            db.session.add(loan)
            db.session.commit()
            flash("قرض کی درخواست کامیابی سے جمع ہو گئی!", "success")
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('add_loan'))
    return render_template("add_loan.html")

@app.route("/download")
def download_excel():
    records = LoanApplication.query.order_by(LoanApplication.created_at.desc()).all()
    if not records:
        flash("کوئی ریکارڈ نہیں ہے ڈاؤن لوڈ کے لیے!", "warning")
        return redirect(url_for('index'))

    data = [{
        "ID": r.id,
        "Name": r.name,
        "CNIC": r.cnic,
        "Address": r.address,
        "Amount": float(r.amount),
        "Purpose": r.purpose,
        "Contact": r.contact,
        "Created At": r.created_at.strftime('%Y-%m-%d %I:%M %p')
    } for r in records]

    df = pd.DataFrame(data)
    file_path = "loan_records.xlsx"
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(debug=True)
