from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import sys

app = Flask(__name__)
app.secret_key = 'abhijit_super_secret_master_key'

# --- Photo Upload Settings ---
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- TiDB Cloud Connection ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://3AAj8oncwkM1Vqv.root:g9N0PtQJp9QVlVka@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Tables (Updated) ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)       # Naya: Name
    phone = db.Column(db.String(20), nullable=False)       # Naya: Phone Number
    text = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(200), nullable=True)  # Naya: Photo ka naam
    status = db.Column(db.String(20), default='Pending')   # Pending -> In Processing -> Solved
    user = db.relationship('User', backref=db.backref('complaints', lazy=True))

with app.app_context():
    try:
        db.create_all()
        print("✅ Database Connected!", file=sys.stderr)
    except Exception as e:
        print("❌ DATABASE ERROR: ", e, file=sys.stderr)

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
            flash("Account created! Please login.", "success")
            return redirect(url_for('index'))
        except:
            flash("Username exists! Try another.", "error")
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
                flash("Invalid Credentials!", "error")
        except:
            flash("Database Error!", "error")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect(url_for('index'))
    user_comps = Complaint.query.filter_by(user_id=session['user_id']).order_by(Complaint.id.desc()).all()
    return render_template('index.html', complaints=user_comps)

@app.route('/add_complaint', methods=['POST'])
def add_complaint():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    c_name = request.form.get('name')
    c_phone = request.form.get('phone')
    c_text = request.form.get('complaint')
    
    # Photo Upload Logic
    filename = None
    if 'photo' in request.files:
        file = request.files['photo']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    if c_name and c_phone and c_text:
        new_c = Complaint(user_id=session['user_id'], name=c_name, phone=c_phone, text=c_text, image_file=filename)
        db.session.add(new_c)
        db.session.commit()
        flash("Complaint submitted successfully!", "success")
    return redirect(url_for('dashboard'))

# Photo dekhne ke liye route
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
            # Pending -> In Processing -> Solved -> Pending (Cycle)
            if comp.status == 'Pending':
                comp.status = 'In Processing'
            elif comp.status == 'In Processing':
                comp.status = 'Solved'
            else:
                comp.status = 'Pending'
            db.session.commit()
            flash(f"Status changed to {comp.status}!", "success")
    return redirect(url_for('admin_panel'))

@app.route('/delete_complaint/<int:id>', methods=['POST'])
def delete_complaint(id):
    if session.get('is_admin'):
        comp = Complaint.query.get(id)
        if comp:
            db.session.delete(comp)
            db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/reset_database')
def reset_database():
    db.drop_all() 
    db.create_all() 
    return "Database Reset Successful! 🎉 Naye features (Name, Phone, Photo) ke sath DB ready hai!"

if __name__ == '__main__':
    app.run(debug=True)