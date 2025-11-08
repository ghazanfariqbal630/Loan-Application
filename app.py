from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import io
import pandas as pd
import random
import string

app = Flask(__name__)
app.secret_key = "your_secret_key"

# PostgreSQL connection
conn = psycopg2.connect(
    host="YOUR_RENDER_DB_HOST",
    database="YOUR_DB_NAME",
    user="YOUR_DB_USER",
    password="YOUR_DB_PASSWORD"
)
cur = conn.cursor()

# Admin user (hardcoded for simplicity)
ADMIN_USER = "admin"
ADMIN_PASS = generate_password_hash("admin123")

# Branch List
branches = [
    {"code":"0012","name":"ISA KHAIL-FU-MLI","district":"Mianwali","sub_region":"Mianwali"},
    {"code":"0014","name":"KALA BAGH-FU-MLI","district":"Mianwali","sub_region":"Mianwali"},
    {"code":"0594","name":"Kundian-FU-MLI","district":"Mianwali","sub_region":"Mianwali"},
    {"code":"0010","name":"MIANWALI-FU-MLI","district":"Mianwali","sub_region":"Mianwali"},
    {"code":"0593","name":"Moch-FU-MLI","district":"Mianwali","sub_region":"Mianwali"},
    {"code":"0013","name":"PIPLAN-FU-MLI","district":"Mianwali","sub_region":"Mianwali"},
    # ... (rest of your branches here)
]

# ======================= LOGIN =======================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USER and check_password_hash(ADMIN_PASS, password):
            session["user"] = "admin"
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid Credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# ======================= DASHBOARD =======================
@app.route("/dashboard")
def dashboard():
    if session.get("user") != "admin":
        flash("Access Denied!", "danger")
        return redirect(url_for("login"))

    search = request.args.get("search", "")
    query = "SELECT * FROM observations"
    if search:
        query += f" WHERE customer_name ILIKE '%{search}%' OR branch_code ILIKE '%{search}%'"
    cur.execute(query)
    records = cur.fetchall()
    return render_template("dashboard.html", records=records, search=search)

# ======================= FORM =======================
@app.route("/form", methods=["GET", "POST"])
def form():
    if session.get("user") != "branch":
        flash("Access Denied!", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        branch_code = request.form["branch_code"]
        branch_name = request.form["branch_name"]
        district = request.form["district"]
        sub_region = request.form["sub_region"]
        customer_name = request.form["customer_name"]
        cnic = request.form["cnic"]
        observation = request.form["client_observation"]
        shared_with = request.form["shared_with"]

        cur.execute(
            """INSERT INTO observations(branch_code, branch_name, district, sub_region,
            customer_name, cnic, client_observation, shared_with) 
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (branch_code, branch_name, district, sub_region, customer_name, cnic, observation, shared_with)
        )
        conn.commit()
        flash("Observation submitted successfully!", "success")
        return redirect(url_for("form"))

    return render_template("form.html", branches=branches)

# ======================= PASSWORD MANAGEMENT =======================
def generate_password(length=8):
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for i in range(length))

@app.route("/manage_passwords", methods=["GET", "POST"])
def manage_passwords():
    if session.get("user") != "admin":
        flash("Access Denied!", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        branch_code = request.form["branch_code"]
        new_pass = generate_password()
        hashed = generate_password_hash(new_pass)
        cur.execute("INSERT INTO branch_passwords (branch_code, password_hash) VALUES (%s,%s) ON CONFLICT (branch_code) DO UPDATE SET password_hash=%s", (branch_code, hashed, hashed))
        conn.commit()
        flash(f"New password generated for branch {branch_code}: {new_pass}", "success")

    cur.execute("SELECT branch_code, password_hash FROM branch_passwords")
    passwords = cur.fetchall()
    return render_template("manage_passwords.html", branches=branches, passwords=passwords)

# ======================= EXCEL DOWNLOAD =======================
@app.route("/download_excel")
def download_excel():
    if session.get("user") != "admin":
        flash("Access Denied!", "danger")
        return redirect(url_for("login"))

    df = pd.read_sql("SELECT * FROM observations", conn)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Observations')
    output.seek(0)
    return send_file(output, attachment_filename="observations.xlsx", as_attachment=True)

# ======================= RUN =======================
if __name__ == "__main__":
    app.run(debug=True)
