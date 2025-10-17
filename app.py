from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# ---------- Flask App Setup ----------
app = Flask(__name__)

# ---------- Database Configuration ----------
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://loan_data_db_user:pjlKJ09B3OVl1XsKHYy9JCosEtZvPB1m@dpg-d3p3eo1r0fns73e12i2g-a.oregon-postgres.render.com/loan_data_db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------- Database Model ----------
class Application(db.Model):
    __tablename__ = "application"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    cnic = db.Column(db.String(20))
    address = db.Column(db.String(200))
    amount = db.Column(db.String(20))
    purpose = db.Column(db.String(200))
    contact = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------- Create Tables if not exist ----------
with app.app_context():
    db.create_all()
    print("✅ PostgreSQL Tables Created Successfully!")

# ---------- Home Page (Form) ----------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"]
        cnic = request.form["cnic"]
        address = request.form["address"]
        amount = request.form["amount"]
        purpose = request.form["purpose"]
        contact = request.form["contact"]

        new_application = Application(
            name=name,
            cnic=cnic,
            address=address,
            amount=amount,
            purpose=purpose,
            contact=contact,
        )

        db.session.add(new_application)
        db.session.commit()
        return redirect("/dashboard")

    return render_template("form.html")

# ---------- Dashboard ----------
@app.route("/dashboard")
def dashboard():
    applications = Application.query.order_by(Application.id.desc()).all()
    return render_template("dashboard.html", applications=applications)

# ---------- Run Locally ----------
if __name__ == "__main__":
    app.run(debug=True)
