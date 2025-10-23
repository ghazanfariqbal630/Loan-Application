# 📁 app.py — Clean PostgreSQL Loan Application System

from flask import Flask, render_template, request, redirect, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import pandas as pd
import os
import io

# ------------------------------
# 1️⃣ Flask App Configuration
# ------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'supersecretkey')

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    "postgresql://loan_data_db_user:pjlKJ09B3OVl1XsKHYy9JCosEtZvPB1m@dpg-d3p3eo1r0fns73e12i2g-a.oregon-postgres.render.com/loan_data_db"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True
}

# Numeric type fix for psycopg2
try:
    import psycopg2.extensions
    NUMERIC_OID = 1700
    psycopg2.extensions.register_type(
        psycopg2.extensions.new_type((NUMERIC_OID,), 'NUMERIC', lambda value, cur: float(value) if value is not None else None)
    )
    print("✅ psycopg2 numeric handler registered.")
except Exception as e:
    print(f"⚠️ psycopg2 numeric handler error: {e}")

db = SQLAlchemy(app)

# ------------------------------
# 2️⃣ Database Model
# ------------------------------
class Application(db.Model):
    __tablename__ = 'application'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    cnic = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
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
            name = request.form.get("name", "").strip()
            cnic = request.form.get("cnic", "").strip()
            address = request.form.get("address", "").strip()
            amount_str = request.form.get("amount", "0").strip()
            purpose = request.form.get("purpose", "").strip()
            contact = request.form.get("contact", "").strip()

            # Server-side validation
            if not name or not cnic or not address or not purpose or not contact:
                flash("تمام خانے پُر کرنا ضروری ہیں۔", "danger")
                return redirect("/")

            if not cnic.replace("-", "").isdigit() or len(cnic.replace("-", "")) != 13:
                flash("CNIC 13 ہندسوں پر مشتمل ہونا چاہیے۔", "danger")
                return redirect("/")

            if not contact.replace("-", "").isdigit() or len(contact.replace("-", "")) != 11:
                flash("رابطہ نمبر 11 ہندسوں پر مشتمل ہونا چاہیے۔", "danger")
                return redirect("/")

            amount = float(amount_str)
            if amount < 1000:
                flash("قرض کی رقم کم از کم ₨ 1,000 ہونی چاہیے۔", "danger")
                return redirect("/")

            new_app = Application(
                name=name, cnic=cnic, address=address,
                amount=amount, purpose=purpose, contact=contact
            )
            db.session.add(new_app)
            db.session.commit()

            flash("درخواست کامیابی سے جمع کر دی گئی!", "success")
            return redirect("/")

        except Exception as e:
            db.session.rollback()
            flash(f"درخواست جمع کرنے میں خرابی: {str(e)}", "danger")
            return redirect("/")

    return render_template("form.html")

# ------------------------------
# 4️⃣ Dashboard
# ------------------------------
@app.route("/dashboard")
def dashboard():
    try:
        applications = Application.query.order_by(Application.created_at.desc()).all()
        total = len(applications)
        total_amount = sum(float(a.amount) for a in applications) if applications else 0
        avg_amount = total_amount / total if total > 0 else 0
        today_count = Application.query.filter(db.func.date(Application.created_at) == date.today()).count()

        return render_template(
            "dashboard.html",
            records=applications,
            total=total,
            total_amount=total_amount,
            avg_amount=avg_amount,
            today_count=today_count
        )
    except Exception as e:
        return f"ڈیش بورڈ لوڈ کرنے میں خرابی: {str(e)}", 500

# ------------------------------
# 5️⃣ Download Data as Excel
# ------------------------------
@app.route("/download")
def download_data():
    try:
        applications = Application.query.order_by(Application.created_at.desc()).all()
        if not applications:
            flash("ڈاؤن لوڈ کرنے کے لیے کوئی ڈیٹا موجود نہیں ہے۔", "warning")
            return redirect("/dashboard")

        data = [{
            "ID": a.id,
            "Name": a.name,
            "CNIC": a.cnic,
            "Address": a.address,
            "Amount": float(a.amount),
            "Purpose": a.purpose,
            "Contact": a.contact,
            "Date": a.created_at.strftime("%Y-%m-%d %H:%M")
        } for a in applications]

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Applications')
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name='loan_applications.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f"ایکسل ڈاؤن لوڈ کرنے میں خرابی: {str(e)}", "danger")
        return redirect("/dashboard")

# ------------------------------
# 6️⃣ Initialize Database
# ------------------------------
tables_created = False
@app.before_request
def create_tables_once():
    global tables_created
    if not tables_created:
        try:
            with app.app_context():
                db.create_all()
                tables_created = True
                print("✅ PostgreSQL Tables Created Successfully!")
        except Exception as e:
            print(f"❌ Tables creation error: {str(e)}")

# ------------------------------
# 7️⃣ Database Session Teardown
# ------------------------------
@app.teardown_request
def teardown_session(exception=None):
    db.session.remove()

# ------------------------------
# 8️⃣ Run App
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
