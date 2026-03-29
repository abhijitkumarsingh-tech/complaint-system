import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Secret key session save karne ke liye bahut zaroori hai
app.secret_key = "abhi_secret_key_123"

# --- MYSQL CONFIG (Password: a@123) ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:a%40123@localhost/complaint_system'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# Database Model
class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(100), default='default.jpg')
    status = db.Column(db.String(20), default='Pending')
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['POST'])
def add_complaint():
    file = request.files.get('file')
    filename = 'default.jpg'
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    new_c = Complaint(name=request.form['name'], email=request.form['email'], 
                      subject=request.form['subject'], message=request.form['message'], image_file=filename)
    db.session.add(new_c)
    db.session.commit()
    return render_template('index.html', tracking_id=new_c.id)

# --- LOGIN LOGIC (Fixed) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        
        # Username: admin | Password: admin7
        if u == 'admin' and p == 'admin7':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash("Galat Username ya Password!", "danger")
            
    return render_template('login.html')

@app.route('/admin')
def admin():
    if not session.get('logged_in'): 
        return redirect(url_for('login'))
    
    t = Complaint.query.count() or 0
    p = Complaint.query.filter_by(status='Pending').count() or 0
    r = Complaint.query.filter_by(status='Resolved').count() or 0
    complaints = Complaint.query.order_by(Complaint.date_posted.desc()).all()
    
    return render_template('admin.html', complaints=complaints, total=t, pending=p, resolved=r)

@app.route('/resolve/<int:id>')
def resolve(id):
    c = Complaint.query.get(id)
    if c:
        c.status = 'Resolved'
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/delete/<int:id>')
def delete(id):
    c = Complaint.query.get(id)
    if c:
        db.session.delete(c)
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/export')
def export():
    c_all = Complaint.query.all()
    data = [{"ID": c.id, "Name": c.name, "Status": c.status, "Subject": c.subject} for c in c_all]
    df = pd.DataFrame(data)
    df.to_excel("report.xlsx", index=False)
    return send_file("report.xlsx", as_attachment=True)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)