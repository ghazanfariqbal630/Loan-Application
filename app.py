from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3, os, io
import pandas as pd
from datetime import datetime

app = Flask(__name__)
DB = "loan_data.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        cnic TEXT,
        address TEXT,
        amount REAL,
        purpose TEXT,
        contact TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET'])
def form():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form.get('name')
    cnic = request.form.get('cnic')
    address = request.form.get('address')
    amount = request.form.get('amount') or 0
    purpose = request.form.get('purpose')
    contact = request.form.get('contact')
    created_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO loans (name, cnic, address, amount, purpose, contact, created_at) VALUES (?,?,?,?,?,?,?)",
              (name, cnic, address, float(amount), purpose, contact, created_at))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM loans ORDER BY id DESC", conn)
    conn.close()
    records = df.to_dict(orient='records')
    total = int(df.shape[0])
    return render_template('dashboard.html', records=records, total=total)

@app.route('/download')
def download():
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM loans ORDER BY id DESC", conn)
    conn.close()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Loans')
    output.seek(0)
    return send_file(output, download_name="loan_applications.xlsx", as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
