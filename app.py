from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os, smtplib, threading, csv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import StringIO
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

# Database Connection (TiDB Cloud / MySQL)
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

# --- HELPERS ---
def send_email_direct(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = ADMIN_EMAIL_DEFAULT
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(ADMIN_EMAIL_DEFAULT, EMAIL_PASSWORD)
        server.sendmail(ADMIN_EMAIL_DEFAULT, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e: 
        print(f"Email Error: {e}")
        return False

@app.template_filter('time_ago')
def time_ago_filter(dt):
    if not dt: return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = datetime.now(timezone.utc) - dt
    if diff.days > 0: return f"{diff.days} days ago"
    hours = diff.seconds // 3600
    if hours > 0: return f"{hours}h ago"
    minutes = (diff.seconds % 3600) // 60
    return "just now" if minutes == 0 else f"{minutes}m ago"

# --- ROUTES ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('admin_panel' if session.get('is_admin') else 'dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        login_mode = request.form.get('login_mode')

        user = User.query.filter_by(username=u, password=p).first()
        
        if user:
            if user.is_admin and login_mode != 'admin_hq':
                flash("Administrative credentials detected. Please use the Administrative Portal.", "error")
                return redirect(url_for('index'))
                
            if user.is_approved or user.is_admin:
                session.permanent = True
                session.update({
                    'user_id': user.id, 
                    'username': user.username, 
                    'is_admin': user.is_admin, 
                    'full_name': user.full_name,
                    'user_email': user.email 
                })
                return redirect(url_for('admin_panel' if user.is_admin else 'dashboard'))
            else:
                flash("Authorization pending. Your account is awaiting administrative approval.", "warning")
                return redirect(url_for('login'))
        
        flash("Invalid identification credentials provided.", "error")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p, e = request.form.get('username'), request.form.get('password'), request.form.get('email')
        ph, fn = request.form.get('phone'), request.form.get('full_name', 'Student')
        code = request.form.get('secret_code')

        if code != SECRET_REGISTRATION_CODE:
            flash("Invalid Campus Authorization Code.", "error")
            return redirect(url_for('register'))

        try:
            new_user = User(username=u, password=p, email=e, phone=ph, full_name=fn, is_admin=False, is_approved=False)
            db.session.add(new_user); db.session.commit()
            flash("Registration successful. Account sent for administrative review.", "success")
            return redirect(url_for('index'))
        except Exception: 
            flash("Account Identifier already exists in system records.", "error")
    return render_template('register.html')

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'): return redirect(url_for('index'))
    stats = {
        'total': Complaint.query.count(),
        'pending': Complaint.query.filter_by(status='Pending').count(),
        'solved': Complaint.query.filter_by(status='Solved').count(),
        'pending_users': User.query.filter_by(is_approved=False, is_admin=False).count()
    }
    all_comps = Complaint.query.order_by(Complaint.created_at.desc()).all()
    all_admins = User.query.filter_by(is_admin=True).all()
    pending_users_list = User.query.filter_by(is_approved=False, is_admin=False).all()
    return render_template('admin.html', complaints=all_comps, stats=stats, admins=all_admins, pending_users=pending_users_list)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if not session.get('is_admin'): return redirect(url_for('index'))
    comp = Complaint.query.get(id)
    if comp:
        comp.admin_remark = request.form.get('remark')
        if comp.status == 'Pending': comp.status = 'In Processing'
        elif comp.status == 'In Processing': comp.status = 'Solved'
        db.session.commit()
        flash("Status updated successfully.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/delete_complaint/<int:id>', methods=['POST'])
def delete_complaint(id):
    if not session.get('is_admin'): return redirect(url_for('index'))
    comp = Complaint.query.get(id)
    if comp:
        db.session.delete(comp); db.session.commit()
        flash("Record purged successfully.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/approve_user/<int:user_id>')
def approve_user(user_id):
    if not session.get('is_admin'): return redirect(url_for('index'))
    user = User.query.get(user_id)
    if user:
        user.is_approved = True
        db.session.commit()
        flash(f"Access granted to {user.username}.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/approve_all_users')
def approve_all_users():
    if not session.get('is_admin'): return redirect(url_for('index'))
    pending = User.query.filter_by(is_approved=False, is_admin=False).all()
    for u in pending: u.is_approved = True
    db.session.commit()
    flash("Batch authorization complete.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/add_complaint', methods=['POST'])
def add_complaint():
    if 'user_id' not in session: return redirect(url_for('index'))
    file = request.files.get('photo')
    if not file or file.filename == '':
        flash("Evidence documentation required.", "error")
        return redirect(url_for('dashboard'))
    fname = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    new_c = Complaint(
        user_id=session['user_id'], name=request.form.get('name'), 
        roll_no=request.form.get('roll_no', '').upper(),
        email=request.form.get('email'), phone=request.form.get('phone'),
        category=request.form.get('category'), priority=request.form.get('priority'),
        text=request.form.get('complaint'), image_file=fname
    )
    db.session.add(new_c); db.session.commit()
    send_email_direct(ADMIN_EMAIL_DEFAULT, "New Incident Report", f"New report by {new_c.name}")
    flash("Report filed successfully.", "success")
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('index'))
    comps = Complaint.query.filter_by(user_id=session['user_id']).order_by(Complaint.created_at.desc()).all()
    return render_template('index.html', complaints=comps, user_email=session.get('user_email'))

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

@app.route('/reset_database')
def reset_database():
    db.drop_all(); db.create_all()
    admin = User(username='admin', password='adminpassword', full_name="ABHIJIT KUMAR SINGH", email=ADMIN_EMAIL_DEFAULT, is_admin=True, is_approved=True)
    db.session.add(admin); db.session.commit()
    return "System Reset Complete. Master Administrator: ABHIJIT KUMAR SINGH initialized."

# if __name__ == '__main__':
#     app.run(debug=True)
if __name__ == '__main__':
    with app.app_context():
        # Ye line jaise hi server chalega, database reset kar degi
        db.drop_all()
        db.create_all()
        admin = User(username='admin', password='adminpassword', full_name="ABHIJIT KUMAR SINGH", email=ADMIN_EMAIL_DEFAULT, is_admin=True, is_approved=True)
        db.session.add(admin)
        db.session.commit()
        print("DATABASE RESET SUCCESSFUL!")
    app.run(debug=True)