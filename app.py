from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os, csv
from io import StringIO
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.secret_key = 'abhijit_super_secret_master_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# --- CONFIGURATION ---
ADMIN_EMAIL_DEFAULT = "abhijitkumarsingh74@gmail.com"  
UPLOAD_FOLDER = 'uploads'
SECRET_REGISTRATION_CODE = "145GPWC" 

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Database Connection
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
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        login_mode = request.form.get('login_mode')
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            if user.is_admin:
                if login_mode == 'admin_hq':
                    session.permanent = True
                    session.update({'user_id': user.id, 'username': user.username, 'is_admin': True, 'full_name': user.full_name})
                    return redirect(url_for('admin_panel'))
                else:
                    flash("Admin account detected. Use Administrative Portal.", "error")
                    return redirect(url_for('login'))
            if not user.is_approved:
                flash("Access Pending. Account awaiting approval.", "warning")
                return redirect(url_for('login'))
            session.permanent = True
            session.update({'user_id': user.id, 'username': user.username, 'is_admin': False, 'user_email': user.email, 'full_name': user.full_name})
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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('is_admin'): return redirect(url_for('login'))
    comps = Complaint.query.filter_by(user_id=session['user_id']).order_by(Complaint.created_at.desc()).all()
    return render_template('index.html', complaints=comps, user_email=session.get('user_email'))

@app.route('/add_complaint', methods=['POST'])
def add_complaint():
    if 'user_id' not in session: return redirect(url_for('login'))
    file = request.files.get('photo')
    if not file or file.filename == '':
        flash("Evidence photo is required.", "error")
        return redirect(url_for('dashboard'))
    fname = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    new_c = Complaint(
        user_id=session['user_id'], name=request.form.get('name'), 
        roll_no=request.form.get('roll_no', '').upper(), email=session.get('user_email', 'N/A'), 
        phone=request.form.get('phone'), category=request.form.get('category'), 
        priority=request.form.get('priority'), text=request.form.get('complaint'), image_file=fname
    )
    db.session.add(new_c); db.session.commit()
    flash("Report filed successfully.", "success")
    return redirect(url_for('dashboard'))

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

@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if not session.get('is_admin'): return redirect(url_for('login'))
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
    if not session.get('is_admin'): return redirect(url_for('login'))
    comp = Complaint.query.get(id)
    if comp:
        db.session.delete(comp); db.session.commit()
        flash("Record purged successfully.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/export_csv')
def export_csv():
    if not session.get('is_admin'): return redirect(url_for('login'))
    comps = Complaint.query.all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Name', 'Roll No', 'Category', 'Status', 'Date'])
    for c in comps:
        cw.writerow([c.id, c.name, c.roll_no, c.category, c.status, c.created_at])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=logs.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/approve_user/<int:user_id>')
def approve_user(user_id):
    if not session.get('is_admin'): return redirect(url_for('login'))
    user = User.query.get(user_id)
    if user:
        user.is_approved = True
        db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/add_new_admin', methods=['POST'])
def add_new_admin():
    if not session.get('is_admin'): return redirect(url_for('login'))
    new_admin = User(username=request.form.get('admin_username'), password=request.form.get('admin_password'), 
                     full_name=request.form.get('admin_full_name'), is_admin=True, is_approved=True)
    db.session.add(new_admin); db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/reset_database')
def reset_database():
    db.drop_all(); db.create_all()
    admin = User(username='admin', password='adminpassword', full_name="ABHIJIT KUMAR SINGH", is_admin=True, is_approved=True)
    db.session.add(admin); db.session.commit()
    return "Database Reset Complete."

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)