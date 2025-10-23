from flask import Flask, render_template, request, redirect, send_file
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
DATA_FILE = "applications.xlsx"

# اگر فائل نہیں ہے تو ہیڈر بنا دو
if not os.path.exists(DATA_FILE):
    df = pd.DataFrame(columns=["ID", "Name", "CNIC", "Address", "Amount", "Purpose", "Contact", "Created_At"])
    df.to_excel(DATA_FILE, index=False)


# 1️⃣ --- Home Page (Form) ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # موجودہ ڈیٹا پڑھو
        df = pd.read_excel(DATA_FILE)

        # نیا ریکارڈ تیار کرو
        new_entry = {
            "ID": len(df) + 1,
            "Name": request.form["name"],
            "CNIC": request.form["cnic"],
            "Address": request.form["address"],
            "Amount": request.form["amount"],
            "Purpose": request.form["purpose"],
            "Contact": request.form["contact"],
            "Created_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # پرانا + نیا ڈیٹا merge کرو
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)

        # Excel میں Save کرو
        df.to_excel(DATA_FILE, index=False)

        return redirect("/dashboard")

    return render_template("form.html")


# 2️⃣ --- Dashboard Page ---
@app.route("/dashboard")
def dashboard():
    df = pd.read_excel(DATA_FILE)
    records = df.to_dict(orient="records")
    return render_template("dashboard.html", records=records, total=len(records))


# 3️⃣ --- Download Excel ---
@app.route("/download")
def download():
    return send_file(DATA_FILE, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
