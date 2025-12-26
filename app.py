from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors

app = Flask(__name__)


app.secret_key = 'your_secret_key_here' 


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'apex'

mysql = MySQL(app)



@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()

        
        if user and check_password_hash(user['password'], password):
            session['loggedin'] = True
            session['id'] = user['id']
            session['username'] = user['first_name']
            
            flash('you was loged with success', 'success')
            return redirect(url_for('home'))
        else:
            flash('email or password is not correct', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone_number = request.form.get('phone_number')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        
        if password != confirm_password:
            flash('passwords is not the same !', 'danger')
            return redirect(url_for('register'))

        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash('email alerady used !', 'warning')
            return redirect(url_for('register'))

       
        hashed_password = generate_password_hash(password)

       
        cursor.execute('''
            INSERT INTO users (first_name, last_name, email, phone_number, password) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (first_name, last_name, email, phone_number, hashed_password))
        
        mysql.connection.commit()

        flash('Account Was created with Succes !', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    flash('you was loged out !', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        return render_template('profile.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'loggedin' in session:
        return render_template('profile.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/articles')
def articles():
    return render_template('articles.html')

@app.route('/article/1')
def article_detail():
    return render_template('article-details1.html')

if __name__ == '__main__':
    app.run(debug=True)