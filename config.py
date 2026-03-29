import os
from dotenv import load_dotenv

# .env फाइल से डेटा लोड करने के लिए
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # 🔐 Security Key (Sessions के लिए)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-123456'
    
    # 🗄️ Database Settings (XAMPP MySQL)
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '') # XAMPP में यह खाली रहता है
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'complaint_system')
    
    # 🔗 SQLAlchemy Connection String
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 📁 Images Upload Folder
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Max 16MB file upload