from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
import pickle
import json
import os
import pandas as pd
import numpy as np
from xhtml2pdf import pisa
import io

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Load trained model and scaler
model = pickle.load(open('rf_classifier.pkl', 'rb'))
scaler = pickle.load(open('scaler.pkl', 'rb'))

# User storage file
users_file = 'users.json'
if not os.path.exists(users_file):
    with open(users_file, 'w') as f:
        json.dump({}, f)


def load_users():
    with open(users_file, 'r') as f:
        return json.load(f)


def save_users(users):
    with open(users_file, 'w') as f:
        json.dump(users, f)


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_users()
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash('User already exists.')
        else:
            users[username] = password
            save_users(users)
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')


@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        try:
            feature_names = [
                'male', 'age', 'currentSmoker', 'cigsPerDay',
                'BPMeds', 'prevalentStroke', 'prevalentHyp', 'diabetes',
                'totChol', 'sysBP', 'diaBP', 'BMI', 'heartRate', 'glucose'
            ]
            features = [float(request.form.get(k)) for k in feature_names]
            input_df = pd.DataFrame([features], columns=feature_names)
            scaled = scaler.transform(input_df)
            prediction = int(model.predict(scaled)[0])

            # ✅ Prepare form data for saving
            form_data = request.form.to_dict()
            form_data['prediction'] = "Yes" if prediction == 1 else "No"
            form_data['username'] = session['username']

            # ✅ Save to Patient.xlsx
            patient_file = 'Patient.xlsx'
            new_row = pd.DataFrame([form_data])

            if os.path.exists(patient_file):
                old_data = pd.read_excel(patient_file)
                all_data = pd.concat([old_data, new_row], ignore_index=True)
            else:
                all_data = new_row

            all_data.to_excel(patient_file, index=False)

            # ✅ Show result page
            return render_template('result.html', prediction=prediction, form_data=request.form)

        except Exception as e:
            return f"Prediction Error: {str(e)}"
    return render_template('form.html')


@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    form_data = request.form.to_dict()
    prediction_text = "You may be at risk of heart disease." if form_data.get(
        'prediction') == '1' else "You are not likely at risk of heart disease."

    # Render HTML template with data
    rendered = render_template('report_template.html', form_data=form_data, prediction_text=prediction_text)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(rendered.encode("UTF-8")), result)

    if not pdf.err:
        response = make_response(result.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=heart_report.pdf'
        return response
    else:
        return "Error generating PDF"


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
