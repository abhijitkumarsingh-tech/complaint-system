from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import sys

app = Flask(__name__)
app.secret_key = 'abhijit_super_secret_master_key'

# --- TiDB Cloud Connection ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://3AAj8oncwkM1Vqv.root:g9N0PtQJp9QVlVka@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Tables ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    user = db.relationship('User', backref=db.backref('complaints', lazy=True))

# --- RENDER FIX: Ye line ab bahar hai taaki Render ise padh sake ---
with app.app_context():
    try:
        db.create_all()
        print("✅ Database Connected & Tables Verified!", file=sys.stderr)
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
            flash("Account successfully created! Please login.", "success")
            return redirect(url_for('index'))
        except Exception as e:
            # Agar DB error aayega toh ab fake message nahi, asli error dikhega
            print("REGISTER ERROR: ", e, file=sys.stderr)
            flash("Database Error! Username exists ya phir connection fail hua.", "error")
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
                flash("Login successful!", "success")
                if user.is_admin:
                    return redirect(url_for('admin_panel'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash("Invalid Username or Password!", "error")
                return redirect(url_for('index'))
        except Exception as e:
            print("LOGIN ERROR: ", e, file=sys.stderr)
            flash("Database Connection Error (500)!", "error")
            return redirect(url_for('index'))
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect(url_for('index'))
    user_comps = Complaint.query.filter_by(user_id=session['user_id']).all()
    return render_template('index.html', complaints=user_comps)

@app.route('/add_complaint', methods=['POST'])
def add_complaint():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    msg = request.form.get('complaint')
    if msg:
        new_c = Complaint(user_id=session['user_id'], text=msg)
        db.session.add(new_c)
        db.session.commit()
        flash("Complaint submitted successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/admin')
def admin_panel():
    if 'user_id' not in session or not session.get('is_admin'):
        flash("Access Denied! Admins only.", "error")
        return redirect(url_for('index'))
    all_comps = Complaint.query.all()
    return render_template('admin.html', complaints=all_comps)

@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if session.get('is_admin'):
        comp = Complaint.query.get(id)
        if comp:
            comp.status = 'Solved' if comp.status == 'Pending' else 'Pending'
            db.session.commit()
            flash("Complaint status updated!", "success")
    return redirect(url_for('admin_panel'))

@app.route('/delete_complaint/<int:id>', methods=['POST'])
def delete_complaint(id):
    if session.get('is_admin'):
        comp = Complaint.query.get(id)
        if comp:
            db.session.delete(comp)
            db.session.commit()
            flash("Complaint deleted permanently!", "success")
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
    # --- DATABASE RESET ROUTE (Sirf ek baar use karne ke liye) ---
@app.route('/reset_database')
def reset_database():
    db.drop_all() # Purani galat tables delete karega
    db.create_all() # Nayi perfect tables banayega (is_admin ke sath)
    return "Database Reset Successful! 🎉 Ab nayi tables ban gayi hain. Wapas jaakar admin account banao!"