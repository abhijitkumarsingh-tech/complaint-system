from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os, smtplib, threading, csv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import StringIO
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'abhijit_super_secret_master_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# --- CONFIGURATION ---
ADMIN_EMAIL_DEFAULT = "abhijitkumarsingh74@gmail.com"  
EMAIL_PASSWORD = "tpclotfvlywdomkf"          
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# TiDB Cloud Connection
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
    progress = db.Column(db.Integer, default=10)
    admin_remark = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- HELPERS ---
def send_email_async(to_email, subject, body):
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
    except Exception as e: print(f"Email Error: {e}")

@app.template_filter('time_ago')
def time_ago_filter(dt):
    if not dt: return ""
    diff = datetime.utcnow() - dt
    if diff.days > 0: return f"{diff.days} days ago"
    hours = diff.seconds // 3600
    if hours > 0: return f"{hours}h ago"
    minutes = (diff.seconds % 3600) // 60
    return "just now" if minutes == 0 else f"{minutes}m ago"

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session.permanent = True
            session.update({
                'user_id': user.id, 
                'username': user.username, 
                'is_admin': user.is_admin, 
                'full_name': user.full_name,
                'user_email': user.email 
            })
            return redirect(url_for('admin_panel' if user.is_admin else 'dashboard'))
        flash("Invalid login credentials", "error")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p, e = request.form.get('username'), request.form.get('password'), request.form.get('email')
        try:
            new_user = User(username=u, password=p, email=e, is_admin=False)
            db.session.add(new_user); db.session.commit()
            flash("Student Account Created! Please login.", "success")
            return redirect(url_for('index'))
        except: flash("Username already exists", "error")
    return render_template('register.html')

@app.route('/add_new_admin', methods=['POST'])
def add_new_admin():
    if not session.get('is_admin'): return redirect(url_for('index'))
    new_u = request.form.get('admin_username')
    new_p = request.form.get('admin_password')
    new_n = request.form.get('admin_full_name')
    new_e = request.form.get('admin_email')
    new_ph = request.form.get('admin_phone')
    try:
        admin_user = User(username=new_u, password=new_p, full_name=new_n, email=new_e, phone=new_ph, is_admin=True)
        db.session.add(admin_user); db.session.commit()
        flash(f"New Admin {new_n} added successfully!", "success")
    except: flash("Admin username already exists!", "error")
    return redirect(url_for('admin_panel'))

# --- DELETE ADMIN ROUTE ---
@app.route('/delete_admin/<int:admin_id>', methods=['POST'])
def delete_admin(admin_id):
    if not session.get('is_admin'): return redirect(url_for('index'))
    
    # Safety Check: Apne aap ko delete nahi kar sakte
    if admin_id == session.get('user_id'):
        flash("Action Denied: You cannot delete your own master account!", "error")
        return redirect(url_for('admin_panel'))
    
    admin_to_del = User.query.get(admin_id)
    if admin_to_del and admin_to_del.is_admin:
        db.session.delete(admin_to_del)
        db.session.commit()
        flash("Admin access has been successfully revoked.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/add_complaint', methods=['POST'])
def add_complaint():
    if 'user_id' not in session: return redirect(url_for('index'))
    file = request.files.get('photo')
    if not file or file.filename == '':
        flash("Evidence photo is mandatory!", "error")
        return redirect(url_for('dashboard'))
    
    fname = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    
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
    db.session.add(new_c); db.session.commit()
    
    e_body = f"New Incident Reported by {new_c.name}\nCategory: {new_c.category}\nIssue: {new_c.text}"
    threading.Thread(target=send_email_async, args=(ADMIN_EMAIL_DEFAULT, "⚠️ New Campus Incident", e_body)).start()
    
    flash("Report submitted successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('index'))
    comps = Complaint.query.filter_by(user_id=session['user_id']).order_by(Complaint.created_at.desc()).all()
    return render_template('index.html', complaints=comps, user_email=session.get('user_email'))

@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'): return redirect(url_for('index'))
    stats = {
        'total': Complaint.query.count(),
        'pending': Complaint.query.filter_by(status='Pending').count(),
        'solved': Complaint.query.filter_by(status='Solved').count()
    }
    all_comps = Complaint.query.order_by(Complaint.created_at.desc()).all()
    # Fetching all admins to show in the Sidebar/Modal list
    all_admins = User.query.filter_by(is_admin=True).all()
    return render_template('admin.html', complaints=all_comps, stats=stats, admins=all_admins)

@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if not session.get('is_admin'): return redirect(url_for('index'))
    comp = Complaint.query.get(id)
    if comp:
        comp.admin_remark = request.form.get('remark')
        if comp.status == 'Pending': 
            comp.status, comp.progress = 'In Processing', 50
        elif comp.status == 'In Processing': 
            comp.status, comp.progress = 'Solved', 100
            s_body = f"Hello {comp.name},\nYour issue ({comp.category}) has been SOLVED.\nRemark: {comp.admin_remark}"
            threading.Thread(target=send_email_async, args=(comp.email, "Status Update: Solved", s_body)).start()
        db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/reset_database')
def reset_database():
    db.drop_all(); db.create_all()
    # Default master admin with full details
    admin = User(username='admin', password='adminpassword', full_name="Abhijit Kumar Singh", email=ADMIN_EMAIL_DEFAULT, is_admin=True)
    db.session.add(admin); db.session.commit()
    return "Database Ready"

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)