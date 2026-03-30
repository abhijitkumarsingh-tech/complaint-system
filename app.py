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

# TiDB / MySQL Connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://3AAj8oncwkM1Vqv.root:g9N0PtQJp9QVlVka@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- HELPERS ---
def send_email_async(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = ADMIN_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(ADMIN_EMAIL, EMAIL_PASSWORD)
        server.sendmail(ADMIN_EMAIL, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Email Error: {e}")

@app.template_filter('time_ago')
def time_ago_filter(dt):
    if not dt: return ""
    diff = datetime.utcnow() - dt
    if diff.days > 0:
        return f"{diff.days} days ago"
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hours ago"
    minutes = (diff.seconds % 3600) // 60
    if minutes == 0: return "just now"
    return f"{minutes} mins ago"

# --- MODELS ---
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
        u = request.form.get('username')
        p = request.form.get('password')
        role = request.form.get('role') 
        if len(p) < 3:
            flash("Password must be at least 3 characters.", "error")
            return redirect(url_for('register'))
        admin_status = True if role == 'Admin' else False
        try:
            new_user = User(username=u, password=p, is_admin=admin_status)
            db.session.add(new_user)
            db.session.commit()
            flash(f"Account created for {role}! Please log in.", "success")
            return redirect(url_for('index'))
        except:
            flash("Username already exists.", "error")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        role = request.form.get('role') 
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            if (role == 'Admin' and not user.is_admin) or (role == 'Student' and user.is_admin):
                flash(f"Access Denied: You are not a {role}.", "error")
                return redirect(url_for('index'))
            session.permanent = True 
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            return redirect(url_for('admin_panel' if user.is_admin else 'dashboard'))
        flash("Invalid Username or Password!", "error")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect(url_for('index'))
    user_comps = Complaint.query.filter_by(user_id=session['user_id']).order_by(Complaint.created_at.desc()).all()
    return render_template('index.html', complaints=user_comps)

@app.route('/add_complaint', methods=['POST'])
def add_complaint():
    if 'user_id' not in session: return redirect(url_for('index'))
    
    name = request.form.get('name')
    roll = request.form.get('roll_no', '').upper() 
    email = request.form.get('email')
    phone = request.form.get('phone')
    cat = request.form.get('category')
    prio = request.form.get('priority', 'Medium')
    msg = request.form.get('complaint')
    
    file = request.files.get('photo')
    filename = secure_filename(file.filename) if file and file.filename else None
    if filename: file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    new_c = Complaint(user_id=session['user_id'], name=name, roll_no=roll, email=email, phone=phone, category=cat, priority=prio, text=msg, image_file=filename)
    db.session.add(new_c)
    db.session.commit()

    # Admin Email Notification
    email_body = f"New Complaint from {name} ({roll})\nCategory: {cat}\nIssue: {msg}"
    threading.Thread(target=send_email_async, args=(ADMIN_EMAIL, f"New Complaint: {cat}", email_body)).start()

    flash("Complaint Filed Successfully!", "success")
    return redirect(url_for('dashboard'))

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
        if comp.status == 'Pending':
            comp.status = 'In Processing'
            comp.progress = 50
        elif comp.status == 'In Processing':
            comp.status = 'Solved'
            comp.progress = 100
            # Student Email Notification
            email_body = f"Hello {comp.name}, your complaint regarding {comp.category} has been SOLVED."
            threading.Thread(target=send_email_async, args=(comp.email, "Complaint Solved!", email_body)).start()
        else:
            comp.status = 'Pending'
            comp.progress = 10
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

@app.route('/download_report')
def download_report():
    if not session.get('is_admin'): return redirect(url_for('index'))
    comps = Complaint.query.all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Name', 'Roll No', 'Phone', 'Category', 'Priority', 'Details', 'Status', 'Submitted At'])
    for c in comps:
        cw.writerow([c.id, c.name, c.roll_no, c.phone, c.category, c.priority, c.text, c.status, c.created_at.strftime('%Y-%m-%d %H:%M:%S')])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=complaint_report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/reset_database')
def reset_database():
    db.drop_all()
    db.create_all()
    return "Database Reset Successful!"

if __name__ == '__main__':
    app.run(debug=True)