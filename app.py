from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'abhijit_secret_key'

# --- TiDB Cloud Database Connection ---
# Ismein SSL aur Pymysql dono set hain taki Cloud par error na aaye
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://3S7mDwgzz7CAvYE.root:FhCoEec4GGP3d35r@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')

# --- Routes ---
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session['user_id'] = user.id
        return redirect(url_for('dashboard'))
    return "Invalid Credentials"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    complaints = Complaint.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', complaints=complaints)

@app.route('/add_complaint', methods=['POST'])
def add_complaint():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    text = request.form['complaint']
    new_complaint = Complaint(user_id=session['user_id'], text=text)
    db.session.add(new_complaint)
    db.session.commit()
    return redirect(url_for('dashboard'))

# --- Final Step: Auto-Create Tables ---
if __name__ == '__main__':
    with app.app_context():
        # Ye line TiDB mein apne aap tables bana degi
        db.create_all()
    app.run(debug=True)