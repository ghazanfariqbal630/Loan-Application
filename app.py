from flask import Flask, render_template, request, redirect, send_file
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

# 🔹 Excel file for saving data
DATA_FILE = "applications.xlsx"

# ---------- 1️⃣ Home Page (Form) ----------
@app.route("/", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        # Get form data
        name = request.form["name"]
        cnic = request.form["cnic"]
        address = request.form["address"]
        amount = request.form["amount"]
        purpose = request.form["purpose"]
        contact = request.form["contact"]
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Save data to Excel
        new_data = pd.DataFrame([{
            "Name": name,
            "CNIC": cnic,
            "Address": address,
            "Amount": amount,
            "Purpose": purpose,
            "Contact": contact,
            "Created_At": created_at
        }])

        # Append or create Excel file
        if os.path.exists(DATA_FILE):
            old_data = pd.read_excel(DATA_FILE)
            df = pd.concat([old_data, new_data], ignore_index=True)
        else:
            df = new_data

        df.to_excel(DATA_FILE, index=False)

        return redirect("/dashboard")

    # 👇 یہ لائن اب form.html render کرے گی
    return render_template("form.html")


# ---------- 2️⃣ Dashboard ----------
@app.route("/dashboard")
def dashboard():
    if os.path.exists(DATA_FILE):
        data = pd.read_excel(DATA_FILE)
        records = data.to_dict(orient="records")
        total = len(records)
    else:
        records = []
        total = 0

    return render_template("dashboard.html", records=records, total=total)


# ---------- 3️⃣ Download Excel ----------
@app.route("/download")
def download():
    if os.path.exists(DATA_FILE):
        return send_file(DATA_FILE, as_attachment=True)
    else:
        return "No data available to download."


# ---------- Run App ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
