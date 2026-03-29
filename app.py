from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'abhijit_super_secret_key' # Session ke liye zaroori hai

# --- TiDB Cloud Database Connection (With SSL) ---
# Ismein mysql+pymysql aur SSL parameters dono hain taaki Cloud par error na aaye
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://3S7mDwgzz7CAvYE.root:FhCoEec4GGP3d35r@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Models (Tables) ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')

# --- Routes (Raste) ---

# 1. Home Page (Login Page)
@app.route('/')
def index():
    return render_template('login.html')

# 2. Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_name = request.form['username']
        pass_word = request.form['password']
        
        # Naya user banane ka logic
        new_user = User(username=user_name, password=pass_word)
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('index'))
        except:
            return "Username already exists! Try another one."
    return render_template('register.html')

# 3. Login Route
@app.route('/login', methods=['POST'])
def login():
    user_name = request.form['username']
    pass_word = request.form['password']
    
    user = User.query.filter_by(username=user_name, password=pass_word).first()
    if user:
        session['user_id'] = user.id
        session['username'] = user.username
        return redirect(url_for('dashboard'))
    return "Invalid Credentials! Please try again."

# 4. Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    # User ki purani complaints nikalna
    user_complaints = Complaint.query.filter_by(user_id=session['user_id']).all()
    return render_template('dashboard.html', complaints=user_complaints)

# 5. Add Complaint Route
@app.route('/add_complaint', methods=['POST'])
def add_complaint():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    comp_text = request.form['complaint']
    new_comp = Complaint(user_id=session['user_id'], text=comp_text)
    db.session.add(new_comp)
    db.session.commit()
    return redirect(url_for('dashboard'))

# 6. Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- Server Start & Table Creation ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Ye line TiDB mein tables apne aap bana degi
    app.run(debug=True)