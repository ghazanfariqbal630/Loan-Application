# ------------------------------
# 📁 app.py — Loan Application System (Render PostgreSQL Version)
# ------------------------------

from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import os

# ------------------------------
# 1️⃣ Flask App Configuration
# ------------------------------
app = Flask(__name__)

# ✅ Render PostgreSQL Database URL
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://loan_data_db_user:pjlKJ09B3OVl1XsKHYy9JCosEtZvPB1m@dpg-d3p3eo1r0fns73e12i2g-a.oregon-postgres.render.com/loan_data_db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------------------
# 2️⃣ Database Model
# ------------------------------
class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    cnic = db.Column(db.String(20))
    address = db.Column(db.String(200))
    amount = db.Column(db.Float)
    purpose = db.Column(db.String(200))
    contact = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Application {self.name}>"

# ------------------------------
# 3️⃣ Home Page (Form)
# ------------------------------
@app.route("/", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        name = request.form["name"]
        cnic = request.form["cnic"]
        address = request.form["address"]
        amount = request.form["amount"]
        purpose = request.form["purpose"]
        contact = request.form["contact"]

        new_app = Application(
            name=name,
            cnic=cnic,
            address=address,
            amount=amount,
            purpose=purpose,
            contact=contact
        )
        db.session.add(new_app)
        db.session.commit()
        return redirect("/dashboard")

    return render_template("form.html")

# ------------------------------
# 4️⃣ Dashboard (Data Table)
# ------------------------------
@app.route("/dashboard")
def dashboard():
    applications = Application.query.order_by(Application.created_at.desc()).all()
    return render_template("dashboard.html", applications=applications)

# ------------------------------
# 5️⃣ Download Data as Excel
# ------------------------------
@app.route("/download")
def download_data():
    applications = Application.query.all()
    if not applications:
        return "No data found!"

    data = [
        {
            "Name": a.name,
            "CNIC": a.cnic,
            "Address": a.address,
            "Amount": a.amount,
            "Purpose": a.purpose,
            "Contact": a.contact,
            "Date": a.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for a in applications
    ]

    df = pd.DataFrame(data)
    file_path = "applications.xlsx"
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

# ------------------------------
# 6️⃣ Initialize Database
# ------------------------------
with app.app_context():
    db.create_all()
    print("✅ PostgreSQL Tables Created Successfully!")

# ------------------------------
# 7️⃣ Run App
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
