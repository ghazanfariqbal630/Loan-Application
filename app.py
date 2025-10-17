from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import io

app = Flask(__name__)

# ---------- DATABASE CONFIG (Render Internal PostgreSQL) ----------
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://loan_data_db_user:pjlKJ09B3OVl1XsKHYy9JCosEtZvPB1m@dpg-d3p3eo1r0fns73e12i2g-a/loan_data_db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------- DATABASE MODEL ----------
class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    cnic = db.Column(db.String(20))
    address = db.Column(db.String(200))
    amount = db.Column(db.Float)
    purpose = db.Column(db.String(200))
    contact = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------- 1️⃣ FORM PAGE ----------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"]
        cnic = request.form["cnic"]
        address = request.form["address"]
        amount = request.form["amount"]
        purpose = request.form["purpose"]
        contact = request.form["contact"]

        new_entry = Application(
            name=name,
            cnic=cnic,
            address=address,
            amount=amount,
            purpose=purpose,
            contact=contact
        )

        db.session.add(new_entry)
        db.session.commit()
        return redirect("/dashboard")

    return render_template("form.html")

# ---------- 2️⃣ DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    records = Application.query.order_by(Application.id.desc()).all()
    total = len(records)
    return render_template("dashboard.html", records=records, total=total)

# ---------- 3️⃣ DOWNLOAD EXCEL ----------
@app.route("/download")
def download_excel():
    records = Application.query.all()
    if not records:
        return "No data to export."

    data = [{
        "ID": r.id,
        "Name": r.name,
        "CNIC": r.cnic,
        "Address": r.address,
        "Amount": r.amount,
        "Purpose": r.purpose,
        "Contact": r.contact,
        "Created At": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for r in records]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    df.to_excel(output, index=False, sheet_name="Applications")
    output.seek(0)

    return send_file(output,
                     download_name="applications.xlsx",
                     as_attachment=True)

# ---------- RUN SERVER ----------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Creates tables if not exist
    app.run(host="0.0.0.0", port=5000, debug=True)
