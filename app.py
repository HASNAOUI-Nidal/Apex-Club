from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import MySQLdb.cursors
import os

app = Flask(__name__)

app.secret_key = 'your_secret_key_here' 

# Database Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'apex'

# Upload Configurations
app.config['PROFILE_UPLOAD_FOLDER'] = 'static/profile_pics'
app.config['IMAGE_UPLOAD_FOLDER'] = 'static/images' # For Events & Articles

mysql = MySQL(app)

# --- PUBLIC ROUTES ---
@app.route('/')
def home():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # 1. Get 3 Newest Articles
    try:
        cursor.execute("SELECT * FROM articles ORDER BY created_at DESC LIMIT 3")
        recent_articles = cursor.fetchall()
    except:
        recent_articles = [] # Handle if table doesn't exist

    # 2. Get 3 Newest Events (ADDED THIS PART)
    try:
        cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 3")
        recent_events = cursor.fetchall()
    except:
        recent_events = []

    cursor.close()
    
    # Send both to the HTML
    return render_template('index.html', recent_articles=recent_articles, recent_events=recent_events)

# --- AUTH SYSTEM (Login/Register/Logout) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password'], password):
            session['loggedin'] = True
            session['user_id'] = user['id'] 
            session['username'] = user['first_name']
            
            flash('You logged in successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Email or password is not correct', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('Email already used!', 'warning')
            cursor.close()
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        default_role = 'Member'
        default_team = None 
        default_image = 'profile.jpg'

        cursor.execute('''
            INSERT INTO users (first_name, last_name, email, phone_number, password, role, team, profile_image) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (first_name, last_name, email, phone_number, hashed_password, default_role, default_team, default_image))
        
        mysql.connection.commit()
        cursor.close()

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear() 
    flash('You have been logged out!', 'info')
    return redirect(url_for('login'))

# --- USER PROFILE SYSTEM ---

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please login to view your profile', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    
    if user_data:
        return render_template('profile.html', user=user_data)
    else:
        session.clear()
        return redirect(url_for('login'))

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone_number')
        bio = request.form.get('bio')
        
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                # Save to profile_pics folder
                file.save(os.path.join(app.root_path, app.config['PROFILE_UPLOAD_FOLDER'], filename))
                cursor.execute("UPDATE users SET profile_image=%s WHERE id=%s", (filename, user_id))

        cursor.execute("""
            UPDATE users 
            SET first_name=%s, last_name=%s, phone_number=%s, bio=%s 
            WHERE id=%s
        """, (first_name, last_name, phone, bio, user_id))
        
        mysql.connection.commit()
        session['username'] = first_name
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    
    return render_template('edit_profile.html', user=user)

# --- MEMBERS SYSTEM ---

@app.route('/members')
def members():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = "SELECT * FROM users WHERE team IS NOT NULL ORDER BY team, role"
    cursor.execute(query)
    all_members = cursor.fetchall()
    cursor.close()
    return render_template('members.html', members=all_members)

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone_number')
        role = request.form.get('role')
        team = request.form.get('team')
        
        password = generate_password_hash("123456")
        
        filename = 'profile.jpg'
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.root_path, app.config['PROFILE_UPLOAD_FOLDER'], filename))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        try:
            cursor.execute('''
                INSERT INTO users (first_name, last_name, email, phone_number, password, role, team, profile_image) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (first_name, last_name, email, phone, password, role, team, filename))
            mysql.connection.commit()
            flash(f'Member {first_name} added successfully!', 'success')
        except Exception as e:
            flash('Error! Maybe email already exists.', 'danger')
        finally:
            cursor.close()
        
        return redirect(url_for('add_member'))

    return render_template('add_member.html')


# --- EVENTS SYSTEM ROUTES ---

@app.route('/events')
def events():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM events ORDER BY id DESC")
    events_data = cursor.fetchall()
    cursor.close()
    return render_template('events.html', events=events_data)


@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        date_str = request.form.get('date_str')
        category = request.form.get('category')
        description = request.form.get('description')
        content = request.form.get('content')
        
        filename = 'default_event.jpg'
        if 'event_image' in request.files:
            file = request.files['event_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                # Save to general images folder
                file.save(os.path.join(app.root_path, app.config['IMAGE_UPLOAD_FOLDER'], filename))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            INSERT INTO events (title, date_str, category, description, content, image)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (title, date_str, category, description, content, filename))
        
        mysql.connection.commit()
        cursor.close()

        flash('Event published successfully!', 'success')
        return redirect(url_for('events'))

    return render_template('add_event.html')

@app.route('/event/<int:id>')
def event_detail(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM events WHERE id = %s", (id,))
    event_data = cursor.fetchone()
    cursor.close()
    
    if event_data:
        return render_template('event_detail.html', event=event_data)
    else:
        flash("Event not found!", "danger")
        return redirect(url_for('events'))


# --- ARTICLES SYSTEM ROUTES ---

@app.route('/articles')
def articles():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Get all articles, newest first
    cursor.execute("SELECT * FROM articles ORDER BY created_at DESC")
    articles_data = cursor.fetchall()
    cursor.close()
    return render_template('articles.html', articles=articles_data)

@app.route('/article/<int:id>')
def article_detail_dynamic(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM articles WHERE id = %s", (id,))
    article = cursor.fetchone()
    cursor.close()
    
    if article:
        return render_template('article_detail.html', article=article)
    else:
        flash("Article not found!", "danger")
        return redirect(url_for('articles'))

@app.route('/add_article', methods=['GET', 'POST'])
def add_article():
    # SECURITY: Only logged-in users can access this page
    if 'user_id' not in session:
        flash("You need to login to publish articles.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        subject = request.form.get('subject') # Math, PC, SVT...
        summary = request.form.get('summary')
        content = request.form.get('content') # From CKEditor

        # Image Upload
        filename = 'default_article.jpg'
        if 'article_image' in request.files:
            file = request.files['article_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                # Save to general images folder
                file.save(os.path.join(app.root_path, app.config['IMAGE_UPLOAD_FOLDER'], filename))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            INSERT INTO articles (title, author, subject, image, summary, content)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (title, author, subject, filename, summary, content))
        
        mysql.connection.commit()
        cursor.close()

        flash('Article published successfully!', 'success')
        return redirect(url_for('articles'))

    return render_template('add_article.html')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)