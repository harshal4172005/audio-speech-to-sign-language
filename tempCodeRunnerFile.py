from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import speech_recognition as sr
import tempfile
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import hashlib
import pandas as pd
from werkzeug.security import generate_password_hash
from flask_mail import Mail, Message
import random
import string
import secrets
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'your_secret_key_here'



# Make sure directories exist
os.makedirs('static/uploads', exist_ok=True)
os.makedirs('feedback', exist_ok=True)

DB_PATH = "users.db"  # Define the database path

# Configure Flask-Mail (replace with your SMTP credentials)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'harshalparekh40@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'hlsa qzmd bhij azji'  # Replace with your app password

mail = Mail(app)

# Dummy database for storing reset tokens
reset_tokens = {}

# Dummy method for hashing passwords (replace with actual hash method)
def hash_password(password):
    return password  # Replace with actual hashing logic like bcrypt or werkzeug

# This is the function that checks the token and validates the user.
def get_user_by_token(token):
    # This function checks the database for the token and validates its expiration.
    user = User.query.filter_by(reset_token=token).first()  # Retrieve the user by token
    if user and user.token_expiry > datetime.utcnow():  # Validate if the token is still valid (not expired)
        return user
    return None

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')  # Get the email entered by the user
        
        if not email:
            flash('Please enter a valid email.', 'error')
            return redirect(url_for('forgot_password'))
        
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=20))  # Generate token
        reset_link = url_for('reset_password', token=token, _external=True)  # Create the reset link
        
        # Create the email message
        msg = Message("Password Reset", sender=app.config['MAIL_USERNAME'], recipients=[email]) 
        msg.body = f'Click the following link to reset your password: {reset_link}'
        
        try:
            mail.send(msg)  # Send email
            flash('Check your inbox for the password reset link!', 'info')  # Success message
            return redirect(url_for('login'))  # Redirect to login page after sending email
        except Exception as e:
            flash(f'Error sending email: {str(e)}', 'error')  # Handle error if email fails to send
            return redirect(url_for('forgot_password'))  # Stay on the forgot-password page if email fails

    return render_template('forgot_password.html')


# Route to handle the password reset
@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = get_user_by_token(token)  # Validate the token and retrieve user
    if not user:
        flash('Invalid or expired token.', 'error')
        return redirect(url_for('login'))  # Redirect to login page if the token is invalid or expired

    # If it's a POST request, handle the password reset
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('reset_password', token=token))

        # Hash the new password (ensure you're using a secure hash method)
        user.password = hash_password(new_password)
        user.reset_token = None  # Remove the token after reset to prevent reuse
        user.token_expiry = None  # Optionally remove the expiry if you're using it

        # Commit the changes to the database (assuming you're using SQLAlchemy)
        db.session.commit()

        flash('Your password has been updated successfully!', 'success')
        return redirect(url_for('login'))  # Redirect to the login page after password reset

    return render_template('reset_password.html', token=token)  # Render the reset password page

def init_db():
    conn = sqlite3.connect(DB_PATH)  # Now this will work
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()



# Function to export all users to Excel
def export_users_to_excel():
    # Ensure the exports directory exists
    os.makedirs('exports', exist_ok=True)
    
    # Connect to the database and get all users
    conn = sqlite3.connect('users.db')
    query = "SELECT id, username, email, created_at FROM users"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Format the timestamp
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['created_at'] = df['created_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Current timestamp for the filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'exports/users_{timestamp}.xlsx'
    
    # Export to Excel
    df.to_excel(filename, index=False, sheet_name='Users')
    
    # Also maintain a current version that always has the latest data
    df.to_excel('exports/users_current.xlsx', index=False, sheet_name='Users')
    
    return filename

# Call database initialization
init_db()

def add_user(username, email, password):
    try:
        # Hash the password securely
        password_hash = generate_password_hash(password)
        
        # Create a database connection
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Insert the user into the database
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Email already exists
        return False
    except Exception as e:
        print(f"Error adding user: {e}")
        return False
    
# Function to validate user login
def validate_login(email, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user[2], password):
        return {'id': user[0], 'username': user[1]}
    return None

# Helper function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Dictionary mapping words to sign language images/GIFs
sign_language_dict = {
    # ASL Dictionary
    "is": {
        # Letters
        "A": "static/A to Z/A.jpg",
        "B": "static/A to Z/B.jpg",
        "C": "static/A to Z/C.jpg",
        "D": "static/A to Z/D.jpg",
        "E": "static/A to Z/E.jpg",
        "F": "static/A to Z/F.jpg",
        "G": "static/A to Z/G.jpg",
        "H": "static/A to Z/H.jpg",
        "I": "static/A to Z/I.jpg",
        "J": "static/A to Z/J.jpg",
        "K": "static/A to Z/K.jpg",
        "L": "static/A to Z/L.jpg",
        "M": "static/A to Z/M.jpg",
        "N": "static/A to Z/N.jpg",
        "O": "static/A to Z/O.jpg",
        "P": "static/A to Z/P.jpg",
        "Q": "static/A to Z/Q.jpg",
        "R": "static/A to Z/R.jpg",
        "S": "static/A to Z/S.jpg",
        "T": "static/A to Z/T.jpg",
        "U": "static/A to Z/U.jpg",
        "V": "static/A to Z/V.jpg",
        "W": "static/A to Z/W.jpg",
        "X": "static/A to Z/X.jpg",
        "Y": "static/A to Z/Y.jpg",
        "Z": "static/A to Z/Z.jpg",
        # Words
        "MORNING": "static/words/morning.gif",
        "DANCE": "static/words/dance.gif",
        "DEAD": "static/words/dead.gif",
        "DEAF": "static/words/deaf.gif",
        "FAMILY": "static/words/family.gif",
        "FOOD": "static/words/food.gif",
        "HELLO": "static/words/hello.gif",
        "JALAPENO": "static/words/jalapeno.gif",
        "NO": "static/words/no.gif",
        "PASTA": "static/words/pasta.gif",
        "PLEASE": "static/words/please.gif",
        "WEEKEND": "static/words/weekend.gif",
        # Sentences
        "GOOD MORNING": "static/Sentences/good morning.gif",
        "GOOD NIGHT": "static/Sentences/good night.gif",
        "HOW ARE YOU": "static/Sentences/how are you doing.gif",
        "WHAT'S UP": "static/Sentences/what_s up.gif",
    },
    # BSL Dictionary - placeholder, replace with actual BSL images
    "bsl": {
        # BSL Alphabet placeholder
        "A": "static/bsl/A.jpg",
        "B": "static/bsl/B.jpg",
        # ... add more BSL signs
    },
    # Indian Sign Language Dictionary - placeholder, replace with actual ISL images
    "asl": {
        # ISL Alphabet placeholder
        "A": "static/isl/A.jpg",
        "B": "static/isl/B.jpg",
        # ... add more ISL signs
    }
}

# Function to find sign language representation for text
def find_sign_for_text(text, language="asl"):
    # Check if language dictionary exists
    if language not in sign_language_dict:
        language = "asl"  # Default to ASL if language not available
    
    lang_dict = sign_language_dict[language]
    
    # First check if the whole text is in the dictionary (for phrases)
    text_upper = text.upper()
    if text_upper in lang_dict:
        return {"found": True, "path": lang_dict[text_upper], "isFullMatch": True}
    
    # If not a full match, return individual word or letter info
    if len(text) == 1 and text.isalpha():
        # It's a single letter
        if text_upper in lang_dict:
            return {"found": True, "path": lang_dict[text_upper], "isFullMatch": False}
    else:
        # It's a word
        if text_upper in lang_dict:
            return {"found": True, "path": lang_dict[text_upper], "isFullMatch": False}
    
    # If we get here, no match found
    return {"found": False}

# Home route - redirects to login if not authenticated
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

# registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        recaptcha_response = request.form.get('g-recaptcha-response')  # 👈 get reCAPTCHA response

        # 1. Validate empty fields
        if not all([username, email, password, recaptcha_response]):
            flash("Please fill all fields and complete the reCAPTCHA.", "error")
            return render_template('register.html', site_key=os.getenv("RECAPTCHA_SITE_KEY"))

        # 2. Verify reCAPTCHA with Google
        secret_key = os.getenv("RECAPTCHA_SECRET_KEY")
        recaptcha_verify_url = 'https://www.google.com/recaptcha/api/siteverify'
        response = requests.post(recaptcha_verify_url, data={
            'secret': secret_key,
            'response': recaptcha_response
        })
        result = response.json()

        if not result.get('success'):
            flash("reCAPTCHA verification failed. Please try again.", "error")
            return render_template('register.html', site_key=os.getenv("RECAPTCHA_SITE_KEY"))

        # 3. Add user to DB
        if add_user(username, email, password):
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        else:
            flash("Email already registered or an error occurred", "error")
            return render_template('register.html', site_key=os.getenv("RECAPTCHA_SITE_KEY"))

    # GET request — render the form
    return render_template('register.html', site_key=os.getenv("RECAPTCHA_SITE_KEY"))

# login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash("Please fill all fields", "error")
            return render_template('login.html')
        
        user = validate_login(email, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password", "error")
            return render_template('login.html')
    
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Admin routes
@app.route('/admin')
def admin_dashboard():
    # Check if user is logged in and has admin privileges
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # In a real app, you'd check for admin role
    # For demo purposes, we'll just show the admin panel to any logged-in user
    
    # Get all users from database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, created_at FROM users")
    users = cursor.fetchall()
    conn.close()
    
    # Get list of Excel export files
    excel_files = []
    if os.path.exists('exports'):
        for filename in os.listdir('exports'):
            if filename.endswith('.xlsx'):
                file_path = os.path.join('exports', filename)
                created_time = datetime.fromtimestamp(os.path.getctime(file_path))
                excel_files.append({
                    'name': filename,
                    'created': created_time.strftime('%Y-%m-%d %H:%M:%S')
                })
    
    # Sort by most recent first
    excel_files.sort(key=lambda x: x['created'], reverse=True)
    
    return render_template('admin.html', users=users, excel_files=excel_files)

# Route to trigger Excel export
@app.route('/admin/export-excel')
def admin_export_excel():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        filename = export_users_to_excel()
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash(f"Error exporting data: {str(e)}", "error")
        return redirect(url_for('admin_dashboard'))

# Route to download Excel files
@app.route('/admin/download-excel/<filename>')
def download_excel(filename):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Security check to prevent directory traversal
    if '..' in filename or filename.startswith('/'):
        return "Invalid filename", 400
    
    file_path = os.path.join('exports', filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found", 404

# API route to get sign language data
@app.route('/get-sign-data')
def get_sign_data():
    text = request.args.get('text', '')
    language = request.args.get('language', 'asl')
    
    if not text:
        return jsonify({"found": False, "error": "No text provided"})
    
    result = find_sign_for_text(text, language)
    return jsonify(result)

# API route for speech recognition through microphone
@app.route('/speech-to-text', methods=['POST'])
def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            print(f"Recognized: {text}")
            return jsonify({"text": text})
        except sr.UnknownValueError:
            return jsonify({"error": "Could not understand the audio."})
        except sr.RequestError:
            return jsonify({"error": "Error connecting to speech recognition service."})

# API route for uploading audio files
@app.route('/upload-audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No file provided"})
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"error": "No file selected"})
    
    # Save the uploaded file temporarily
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, secure_filename(audio_file.filename))
    audio_file.save(file_path)
    
    # Process with speech recognition
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(file_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": f"Error processing audio: {str(e)}"})
    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

# API route for feedback submission
@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    if not data or 'feedback' not in data:
        return jsonify({"success": False, "error": "No feedback provided"})
    
    feedback = data['feedback']
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save feedback to a file
    try:
        filename = f"feedback/feedback_{timestamp}.txt"
        with open(filename, 'w') as f:
            f.write(feedback)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# API route for user authentication (simplified for demo)
@app.route('/api/auth', methods=['POST'])
def auth():
    data = request.json
    # In a real app, validate credentials against a database
    # This is a simplified mock implementation
    if data.get('email') and data.get('password'):
        return jsonify({"success": True, "user": {"name": "Demo User"}})
    return jsonify({"success": False, "error": "Invalid credentials"})

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/help')
def help():
    return render_template('help.html')

if __name__ == '__main__':
    # Initialize the database
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
