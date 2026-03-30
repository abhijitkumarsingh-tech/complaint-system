from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import csv  # 🔥 NAYA: Excel/CSV Report ke liye
from io import StringIO

app = Flask(__name__)
app.secret_key = 'abhijit_super_secret_master_key'

# ==========================================
# 🛑 ADMIN EMAIL SETTINGS
# ==========================================
ADMIN_EMAIL = "abhijitkumarsingh74@gmail.com"  
EMAIL_PASSWORD = "tpclotfvlywdomkf"        
# ==========================================

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://3AAj8oncwkM1Vqv.root:g9N0PtQJp9QVlVka@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def send_email(to_email, subject, body):
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
        print("EMAIL ERROR: ", e, file=sys.stderr)

# --- Database Tables ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='General') # 🔥 NAYA: Category
    priority = db.Column(db.String(20), nullable=False, default='Medium')  # 🔥 NAYA: Priority
    text = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Pending')
    user = db.relationship('User', backref=db.backref('complaints', lazy=True))

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        pass

# --- Routes ---
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        admin_status = True if u.lower() == 'admin' else False
        try:
            new_user = User(username=u, password=p, is_admin=admin_status)
            db.session.add(new_user)
            db.session.commit()
            flash("Account successfully created! Please log in.", "success")
            return redirect(url_for('index'))
        except:
            flash("Username already exists. Please try another one.", "error")
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        try:
            user = User.query.filter_by(username=u, password=p).first()
            if user:
                session['user_id'] = user.id
                session['is_admin'] = user.is_admin
                if user.is_admin:
                    return redirect(url_for('admin_panel'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash("Invalid Credentials! Please try again.", "error")
        except:
            flash("Database Connection Error. Please try again later.", "error")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect(url_for('index'))
    user_comps = Complaint.query.filter_by(user_id=session['user_id']).order_by(Complaint.id.desc()).all()
    return render_template('index.html', complaints=user_comps)

@app.route('/add_complaint', methods=['GET', 'POST'])
def add_complaint():
    if request.method == 'GET':
        return redirect(url_for('dashboard'))

    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    try:
        c_name = request.form.get('name')
        c_email = request.form.get('email')
        c_phone = request.form.get('phone')
        c_category = request.form.get('category') # 🔥 Get Category
        c_priority = request.form.get('priority') # 🔥 Get Priority
        c_text = request.form.get('complaint')
        
        filename = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename != '':
                filename = secure_filename(file.filename)
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        if c_name and c_email and c_phone and c_text:
            new_c = Complaint(user_id=session['user_id'], name=c_name, email=c_email, phone=c_phone, category=c_category, priority=c_priority, text=c_text, image_file=filename)
            db.session.add(new_c)
            db.session.commit()
            
            subject = f"[{c_priority} Priority] New Complaint: {c_category}"
            body = f"Hello Admin,\n\nA new complaint has been registered.\n\nCategory: {c_category}\nPriority: {c_priority}\nStudent: {c_name}\n\nDetails:\n{c_text}"
            threading.Thread(target=send_email, args=(ADMIN_EMAIL, subject, body)).start()

            flash("Complaint submitted successfully!", "success")
        else:
            flash("All fields are required!", "error")

    except Exception as e:
        print("CRITICAL ERROR IN ADD_COMPLAINT: ", e, file=sys.stderr)
        flash("Technical Error. Please try again.", "error")

    return redirect(url_for('dashboard'))

# 🔥 NAYA ROUTE: Download Excel/CSV Report
@app.route('/download_report')
def download_report():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    
    comps = Complaint.query.all()
    si = StringIO()
    cw = csv.writer(si)
    
    # Excel ke Headers (Pehli Line)
    cw.writerow(['Complaint ID', 'Student Name', 'Phone', 'Email', 'Department', 'Priority Level', 'Issue Description', 'Current Status'])
    
    # Database ka data Excel mein dalna
    for c in comps:
        cw.writerow([c.id, c.name, c.phone, c.email, c.category, c.priority, c.text, c.status])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=complaint_report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/admin')
def admin_panel():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('index'))
    all_comps = Complaint.query.order_by(Complaint.id.desc()).all()
    return render_template('admin.html', complaints=all_comps)

@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if session.get('is_admin'):
        comp = Complaint.query.get(id)
        if comp:
            if comp.status == 'Pending':
                comp.status = 'In Processing'
            elif comp.status == 'In Processing':
                comp.status = 'Solved'
                subject = f"Status Update: Complaint #{comp.id} Solved"
                body = f"Hello {comp.name},\n\nYour complaint regarding '{comp.category}' has been SOLVED."
                threading.Thread(target=send_email, args=(comp.email, subject, body)).start()
            else:
                comp.status = 'Pending'
            db.session.commit()
            flash(f"Status updated to '{comp.status}'.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/delete_complaint/<int:id>', methods=['POST'])
def delete_complaint(id):
    if session.get('is_admin'):
        comp = Complaint.query.get(id)
        if comp:
            db.session.delete(comp)
            db.session.commit()
            flash("Complaint record deleted permanently.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/reset_database')
def reset_database():
    db.drop_all() 
    db.create_all() 
    return "Database Reset Successful! The system is now fully configured with Categories, Priorities and Export features!"

if __name__ == '__main__':
    app.run(debug=True)