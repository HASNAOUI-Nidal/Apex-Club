from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename # ضروري باش نصلحو سمية الصورة
import MySQLdb.cursors
import os # ضروري باش نتعاملو مع الملفات

app = Flask(__name__)

app.secret_key = 'your_secret_key_here' 

# إعدادات الداتابيز
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'apex'

# إعدادات رفع الصور (Upload Config)
# هادي كتعني: الصور غيتحطو فـ static/profile_pics
app.config['UPLOAD_FOLDER'] = 'static/profile_pics'

mysql = MySQL(app)

@app.route('/')
def home():
    return render_template('index.html')

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

# === دالة التعديل الجديدة (The New Edit Function) ===
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    # 1. التأكد من تسجيل الدخول
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 2. إذا ضغط الزر Save (POST)
    if request.method == 'POST':
        # جيب المعلومات النصية
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone_number')
        bio = request.form.get('bio')
        
        # 3. معالجة الصورة (Image Upload)
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            
            # واش الملف عندو سمية ومفرغش؟
            if file.filename != '':
                filename = secure_filename(file.filename)
                # حفظ الصورة في المسار المحدد
                file.save(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename))
                
                # تحديث اسم الصورة في الداتابيز
                cursor.execute("UPDATE users SET profile_image=%s WHERE id=%s", (filename, user_id))

        # 4. تحديث باقي المعلومات
        cursor.execute("""
            UPDATE users 
            SET first_name=%s, last_name=%s, phone_number=%s, bio=%s 
            WHERE id=%s
        """, (first_name, last_name, phone, bio, user_id))
        
        mysql.connection.commit()
        
        # تحديث السيشن إذا تبدلات السمية
        session['username'] = first_name
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    # 3. إذا بغا يشوف الفورم (GET) - كنجيبو معلوماتو القديمة
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    
    return render_template('edit_profile.html', user=user)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('user_id', None)
    session.pop('username', None)
    flash('You have been logged out!', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please login to view your profile', 'warning')
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    query = "SELECT first_name, last_name, email, phone_number, bio, role, team, profile_image FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    
    if user_data:
        return render_template('profile.html', user=user_data)
    else:
        session.clear()
        return redirect(url_for('login'))

@app.route('/articles')
def articles():
    return render_template('articles.html')

@app.route('/members')
def members():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # كنجيبو غير الناس اللي عندهم فريق (يعني ماشي يوزرز عاديين)
    # كنرتبوهم بـ Team باش يسهل علينا العرض
    query = "SELECT * FROM users WHERE team IS NOT NULL ORDER BY team, role"
    cursor.execute(query)
    all_members = cursor.fetchall()
    cursor.close()
    
    return render_template('members.html', members=all_members)

@app.route('/article/1')
def article_detail():
    return render_template('article-details1.html')

# أضف هذا الكود في app.py

@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    # حماية الصفحة: غير نتا (اللي مكونيكطي) اللي تقدر تدخل ليها
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # 1. جمع المعلومات من الفورم
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone_number')
        role = request.form.get('role')      # مثال: President, Volunteer
        team = request.form.get('team')      # مثال: Board, IT, Volunteer
        
        # 2. إنشاء مود باس افتراضي (123456)
        password = generate_password_hash("123456")
        
        # 3. معالجة الصورة
        filename = 'profile.jpg' # الصورة الافتراضية إلا ماخترتيش صورة
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                # حفظ الصورة
                file.save(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename))

        # 4. الإدخال في الداتابيز
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
        
        # البقاء في نفس الصفحة لإضافة عضو آخر بسرعة
        return redirect(url_for('add_member'))

    return render_template('add_member.html')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)