# ------------------------------
# 📁 app.py — Loan Application System (Render PostgreSQL Version)
# ------------------------------

from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import pandas as pd
import os

# ------------------------------
# 1️⃣ Flask App Configuration
# ------------------------------
app = Flask(__name__)

# ✅ Render PostgreSQL Database URL
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://loan_data_db_user:pjlKJ09B3OVl1XsKHYy9JCosEtZvPB1m@dpg-d3p3eo1r0fns73e12i2g-a.oregon-postgres.render.com/loan_data_db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

db = SQLAlchemy(app)

# ------------------------------
# 2️⃣ Database Model (PostgreSQL compatible)
# ------------------------------
class Application(db.Model):
    __tablename__ = 'application'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cnic = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)  # Changed to Text for PostgreSQL
    amount = db.Column(db.Numeric(10, 2), nullable=False)  # Changed to Numeric for PostgreSQL
    purpose = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Application {self.name}>"

# ------------------------------
# 3️⃣ Home Page (Form)
# ------------------------------
@app.route("/", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        try:
            name = request.form["name"]
            cnic = request.form["cnic"]
            address = request.form["address"]
            amount = float(request.form["amount"])
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
        except Exception as e:
            db.session.rollback()
            return f"Error: {str(e)}", 400

    return render_template("form.html")

# ------------------------------
# 4️⃣ Dashboard (Data Table)
# ------------------------------
@app.route("/dashboard")
def dashboard():
    try:
        applications = Application.query.order_by(Application.created_at.desc()).all()
        
        # Calculate statistics
        total = len(applications)
        total_amount = sum(float(app.amount) for app in applications) if applications else 0
        avg_amount = total_amount / total if total > 0 else 0
        
        # Count today's applications
        today = date.today()
        today_count = Application.query.filter(
            db.func.date(Application.created_at) == today
        ).count()
        
        return render_template("dashboard.html", 
                             records=applications, 
                             total=total,
                             total_amount=total_amount,
                             avg_amount=avg_amount,
                             today_count=today_count)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

# ------------------------------
# 5️⃣ Download Data as Excel
# ------------------------------
@app.route("/download")
def download_data():
    try:
        applications = Application.query.all()
        if not applications:
            return "No data found!"

        data = [
            {
                "ID": a.id,
                "Name": a.name,
                "CNIC": a.cnic,
                "Address": a.address,
                "Amount": float(a.amount),
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
    except Exception as e:
        return f"Error downloading data: {str(e)}", 500

# ------------------------------
# 6️⃣ Initialize Database
# ------------------------------
@app.before_first_request
def create_tables():
    try:
        db.create_all()
        print("✅ PostgreSQL Tables Created Successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")

# ------------------------------
# 7️⃣ Run App
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
