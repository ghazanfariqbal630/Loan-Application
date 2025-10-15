from flask import Flask, render_template, request, redirect, url_for, send_file
import pandas as pd
import sqlite3
import io

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('loan_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS loan_applications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  cnic TEXT,
                  address TEXT,
                  amount REAL,
                  purpose TEXT,
                  contact TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        name = request.form['name']
        cnic = request.form['cnic']
        address = request.form['address']
        amount = request.form['amount']
        purpose = request.form['purpose']
        contact = request.form['contact']

        conn = sqlite3.connect('loan_data.db')
        c = conn.cursor()
        c.execute("INSERT INTO loan_applications (name, cnic, address, amount, purpose, contact) VALUES (?, ?, ?, ?, ?, ?)",
                  (name, cnic, address, amount, purpose, contact))
        conn.commit()
        conn.close()

        return redirect(url_for('success'))

    return render_template('form.html')

@app.route('/success')
def success():
    return "<h2>✅ Loan Application Submitted Successfully!</h2><a href='/'>Back</a>"

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('loan_data.db')
    df = pd.read_sql_query("SELECT * FROM loan_applications", conn)
    conn.close()
    return render_template('dashboard.html', tables=df.to_dict(orient='records'))

@app.route('/download')
def download():
    conn = sqlite3.connect('loan_data.db')
    df = pd.read_sql_query("SELECT * FROM loan_applications", conn)
    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Loan Applications')
    output.seek(0)

    return send_file(output, download_name="loan_applications.xlsx", as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
