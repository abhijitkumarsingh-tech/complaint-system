from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import csv
from io import StringIO
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'abhijit_super_secret_master_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# --- CONFIGURATION ---
ADMIN_EMAIL = "abhijitkumarsingh74@gmail.com"  
EMAIL_PASSWORD = "tpclotfvlywdomkf"        
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# TiDB / MySQL Database Connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://3AAj8oncwkM1Vqv.root:g9N0PtQJp9QVlVka@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- FILTERS (For Time Tracking) ---
@app.template_filter('time_ago')
def time_ago_filter(dt):
    if not dt: return ""
    diff = datetime.utcnow() - dt
    if diff.days > 0: return f"{diff.days} days ago"
    hours = diff.seconds // 3600
    if hours > 0: return f"{hours} hours ago"
    minutes = (diff.seconds % 3600) // 60
    if minutes == 0: return "just now"
    return f"{minutes} mins ago"

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    roll_no = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default='Medium')
    text = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Pending')
    progress = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('complaints', lazy=True))

with app.app_context():
    db.create_all()

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p, role = request.form.get('username'), request.form.get('password'), request.form.get('role')
        if len(p) < 3:
            flash("Password too short!", "error")
            return redirect(url_for('register'))
        admin_status = True if role == 'Admin' else False
        try:
            new_user = User(username=u, password=p, is_admin=admin_status)
            db.session.add(new_user)
            db.session.commit()
            flash(f"Account created for {role}!", "success")
            return redirect(url_for('index'))
        except:
            flash("Username already exists.", "error")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p, role = request.form.get('username'), request.form.get('password'), request.form.get('role')
        user = User.query.filter_by(username=u, password=p).first()
        if user and ((role == 'Admin' and user.is_admin) or (role == 'Student' and not user.is_admin)):
            session.permanent = True 
            session['user_id'], session['username'], session['is_admin'] = user.id, user.username, user.is_admin
            return redirect(url_for('admin_panel' if user.is_admin else 'dashboard'))
        flash("Invalid Credentials!", "error")
    return render_template('login.html')

@app.route('/add_complaint', methods=['POST'])
def add_complaint():
    if 'user_id' not in session: return redirect(url_for('index'))
    
    file = request.files.get('photo')
    fname = secure_filename(file.filename) if file and file.filename else None
    if fname: file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))

    new_c = Complaint(
        user_id=session['user_id'],
        name=request.form.get('name'),
        roll_no=request.form.get('roll_no', '').upper(),
        email=request.form.get('email'),
        phone=request.form.get('phone'),
        category=request.form.get('category'),
        priority=request.form.get('priority'),
        text=request.form.get('complaint'),
        image_file=fname
    )
    db.session.add(new_c)
    db.session.commit()
    flash("Complaint Filed Successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('index'))
    comps = Complaint.query.filter_by(user_id=session['user_id']).order_by(Complaint.created_at.desc()).all()
    return render_template('index.html', complaints=comps)

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'): return redirect(url_for('index'))
    all_comps = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template('admin.html', complaints=all_comps)

@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if not session.get('is_admin'): return redirect(url_for('index'))
    comp = Complaint.query.get(id)
    if comp:
        if comp.status == 'Pending': comp.status, comp.progress = 'In Processing', 50
        elif comp.status == 'In Processing': comp.status, comp.progress = 'Solved', 100
        else: comp.status, comp.progress = 'Pending', 10
        db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/delete_complaint/<int:id>', methods=['POST'])
def delete_complaint(id):
    if not session.get('is_admin'): return redirect(url_for('index'))
    comp = Complaint.query.get(id)
    if comp:
        db.session.delete(comp)
        db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/reset_database')
def reset_database():
    db.drop_all()
    db.create_all()
    return "Database Reset Successful! All new columns (Roll No, Time, Priority) are ready."

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)