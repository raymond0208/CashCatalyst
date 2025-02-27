import os
from dotenv import load_dotenv

# Load .env file explicitly at the start
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, '..', 'instance', 'cash_flow.db')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-default-secret-key-for-development'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Load API key with more detailed logging
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    if not ANTHROPIC_API_KEY:
        print("WARNING: ANTHROPIC_API_KEY not found in environment variables")
    
    UPLOAD_FOLDER = os.path.join(basedir, '..', 'uploads')

    # Enhanced debugging information
    print(f"Configuration initialized:")
    print(f"- Database path: {db_path}")
    print(f"- Anthropic API Key status: {'Set' if ANTHROPIC_API_KEY else 'Not set'}")
    print(f"- API Key length: {len(ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else 0}")