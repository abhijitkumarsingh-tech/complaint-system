from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.secret_key = 'abhijit_super_secret_master_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# --- CONFIGURATION ---
ADMIN_EMAIL_DEFAULT = "abhijitkumarsingh74@gmail.com"  
EMAIL_PASSWORD = "duoj jfam rucl nute"          
UPLOAD_FOLDER = 'uploads'
SECRET_REGISTRATION_CODE = "145GPWC" 

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Database Connection (TiDB Cloud)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://3AAj8oncwkM1Vqv.root:g9N0PtQJp9QVlVka@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=True) 
    phone = db.Column(db.String(20), nullable=True)  
    full_name = db.Column(db.String(100), default="User")
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    roll_no = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), default='Medium')
    text = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    admin_remark = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# --- FILTERS ---
@app.template_filter('time_ago')
def time_ago_filter(dt):
    if not dt: return ""
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    diff = datetime.now(timezone.utc) - dt
    if diff.days > 0: return f"{diff.days} days ago"
    hours = diff.seconds // 3600
    if hours > 0: return f"{hours}h ago"
    return f"{diff.seconds // 60}m ago"

# --- ROUTES ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('admin_panel' if session.get('is_admin') else 'dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        login_mode = request.form.get('login_mode')

        user = User.query.filter_by(username=u, password=p).first()
        
        if user:
            # 1. Admin mode check
            if user.is_admin:
                if login_mode == 'admin_hq':
                    session.permanent = True
                    session.update({'user_id': user.id, 'username': user.username, 'is_admin': True, 'full_name': user.full_name})
                    return redirect(url_for('admin_panel'))
                else:
                    flash("Admin account detected. Use Administrative Portal.", "error")
                    return redirect(url_for('login'))
            
            # 2. Student Approval Check (Most Important Fix)
            if not user.is_approved:
                flash("Access Pending. Account awaiting administrative approval.", "warning")
                return redirect(url_for('login'))

            # 3. Successful Student Login
            session.permanent = True
            session.update({
                'user_id': user.id, 
                'username': user.username, 
                'is_admin': False,
                'user_email': user.email,
                'full_name': user.full_name
            })
            return redirect(url_for('dashboard'))
        
        flash("Invalid Credentials.", "error")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p, e = request.form.get('username'), request.form.get('password'), request.form.get('email')
        ph, fn = request.form.get('phone'), request.form.get('full_name', 'Student')
        code = request.form.get('secret_code')

        if code != SECRET_REGISTRATION_CODE:
            flash("Invalid Authorization Code.", "error")
            return redirect(url_for('register'))

        try:
            new_user = User(username=u, password=p, email=e, phone=ph, full_name=fn, is_admin=False, is_approved=False)
            db.session.add(new_user); db.session.commit()
            flash("Registration successful. Wait for Admin approval.", "success")
            return redirect(url_for('login'))
        except Exception: 
            flash("Username already exists.", "error")
    return render_template('register.html')

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'): return redirect(url_for('login'))
    stats = {
        'total': Complaint.query.count(),
        'pending': Complaint.query.filter_by(status='Pending').count(),
        'solved': Complaint.query.filter_by(status='Solved').count(),
        'pending_users': User.query.filter_by(is_approved=False, is_admin=False).count()
    }
    all_comps = Complaint.query.order_by(Complaint.created_at.desc()).all()
    all_admins = User.query.filter_by(is_admin=True).all()
    pending_users = User.query.filter_by(is_approved=False, is_admin=False).all()
    return render_template('admin.html', complaints=all_comps, stats=stats, admins=all_admins, pending_users=pending_users)

@app.route('/approve_user/<int:user_id>')
def approve_user(user_id):
    if not session.get('is_admin'): return redirect(url_for('login'))
    user = User.query.get(user_id)
    if user:
        user.is_approved = True
        db.session.commit()
        flash(f"Access granted to {user.username}.", "success")
    return redirect(url_for('admin_panel'))
@app.route('/add_new_admin', methods=['POST'])
def add_new_admin():
    if not session.get('is_admin'): return redirect(url_for('login'))
    fn = request.form.get('admin_full_name')
    u = request.form.get('admin_username')
    p = request.form.get('admin_password')
    
    try:
        new_admin = User(username=u, password=p, full_name=fn, is_admin=True, is_approved=True)
        db.session.add(new_admin)
        db.session.commit()
        flash(f"Administrator {u} authorized successfully.", "success")
    except:
        flash("Username already exists.", "error")
    return redirect(url_for('admin_panel'))
@app.route('/reset_database')
def reset_database():
    db.drop_all(); db.create_all()
    admin = User(username='admin', password='adminpassword', full_name="ABHIJIT KUMAR SINGH", is_admin=True, is_approved=True)
    db.session.add(admin); db.session.commit()
    return "DB Cleaned. Master Admin: admin / adminpassword"

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # Auto-Reset Logic Hata di gayi hai taaki data save rahe
    app.run(debug=True)