from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import sqlite3
import os
from sentiment_analysis import get_star_rating

# Get the absolute path to the templates directory
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))

app = Flask(__name__, 
            template_folder=template_dir,
            static_folder=static_dir)
app.secret_key = 'your_secret_key'
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Force template reloading
app.jinja_env.auto_reload = True  # Force Jinja2 template reloading

# Add cache control headers
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Ensure the instance folder exists
if not os.path.exists('instance'):
    os.makedirs('instance')

# Database setup (create tables if they don't exist)
def init_db():
    with sqlite3.connect('instance/users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_name TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            review_text TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )''')
        conn.commit()

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        print("Form data received:", request.form.keys())
        if 'username' not in request.form or 'email' not in request.form or 'password' not in request.form:
            print("Missing form data")
            # You could render the signup template again with an error message
            return "Missing form data! Please fill out all fields.", 400 # Or redirect to signup page with error

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        with sqlite3.connect('instance/users.db') as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', (username, email, password))
                conn.commit()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                return "Email already exists."

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        with sqlite3.connect('instance/users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE email = ? AND password = ?', (email, password))
            user = cursor.fetchone()
            if user:
                session['user_id'] = user[0]
                return redirect(url_for('dashboard'))
            else:
                return "Login failed. Please check your credentials."

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    with sqlite3.connect('instance/users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        cursor.execute('SELECT COUNT(*) FROM purchases WHERE user_id = ?', (user_id,))
        purchase_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM reviews WHERE user_id = ?', (user_id,))
        review_count = cursor.fetchone()[0]
    return render_template('dashboard.html', user=user, purchase_count=purchase_count, review_count=review_count)

@app.route('/product_listing', methods=['GET'])
def product_listing():
    with sqlite3.connect('instance/users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products')
        products = cursor.fetchall()

        # Fetch reviews for each product, including username
        product_reviews = {}
        for product in products:
            cursor.execute('''
                SELECT reviews.id, users.username, reviews.review_text
                FROM reviews
                JOIN users ON reviews.user_id = users.id
                WHERE reviews.product_id = ?
            ''', (product[0],))
            reviews = cursor.fetchall()
            product_reviews[product[0]] = reviews

    return render_template('product_listing.html', products=products, product_reviews=product_reviews)

@app.route('/purchase_product/<int:product_id>', methods=['POST'])
def purchase_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    with sqlite3.connect('instance/users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        if product:
            cursor.execute('INSERT INTO purchases (user_id, product_name) VALUES (?, ?)', (user_id, product[0]))
            conn.commit()

    return redirect(url_for('purchase_history'))

@app.route('/purchase_history')
def purchase_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    with sqlite3.connect('instance/users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT product_name FROM purchases WHERE user_id = ?', (user_id,))
        purchases = cursor.fetchall()

    return render_template('purchase_history.html', purchases=purchases)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        product_name = request.form['product_name']
        description = request.form['description']
        price = request.form['price']

        with sqlite3.connect('instance/users.db') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO products (name, description, price) VALUES (?, ?, ?)', (product_name, description, price))
            conn.commit()

        return redirect(url_for('product_listing'))

    return render_template('add_product.html')

@app.route('/submit_review/<int:product_id>', methods=['POST'])
def submit_review(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    review_text = request.form['review_text']

    with sqlite3.connect('instance/users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO reviews (user_id, product_id, review_text) VALUES (?, ?, ?)', 
                       (user_id, product_id, review_text))
        conn.commit()

    return redirect(url_for('product_listing'))

@app.route('/detect_reviews/<int:product_id>', methods=['POST'])
def detect_reviews(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect('instance/users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, review_text FROM reviews WHERE product_id = ?', (product_id,))
        reviews = cursor.fetchall()

        genuine_reviews = []
        non_genuine_reviews = []

        for user_id, review_text in reviews:
            cursor.execute('SELECT COUNT(*) FROM purchases WHERE user_id = ? AND product_name = (SELECT name FROM products WHERE id = ?)', 
                           (user_id, product_id))
            purchase_count = cursor.fetchone()[0]

            if purchase_count > 0:
                genuine_reviews.append(review_text)
            else:
                non_genuine_reviews.append(review_text)

    return render_template('product_reviews.html', 
                           genuine_reviews=genuine_reviews, 
                           non_genuine_reviews=non_genuine_reviews)

@app.route('/product_rating/<int:product_id>')
def product_rating(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with sqlite3.connect('instance/users.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name, description FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        cursor.execute('SELECT user_id, review_text FROM reviews WHERE product_id = ?', (product_id,))
        reviews = cursor.fetchall()

        genuine_reviews = []
        total_score = 0
        count = 0

        for user_id, review_text in reviews:
            cursor.execute('SELECT COUNT(*) FROM purchases WHERE user_id = ? AND product_name = (SELECT name FROM products WHERE id = ?)',
                           (user_id, product_id))
            purchase_count = cursor.fetchone()[0]

            if purchase_count > 0:
                rating = get_star_rating(review_text)
                genuine_reviews.append({'text': review_text, 'rating': rating})
                total_score += rating
                count += 1

    avg_rating = round(total_score / count, 2) if count > 0 else "No genuine reviews yet"

    return render_template('product_rating.html', 
                           product=product,
                           genuine_reviews=genuine_reviews,
                           avg_rating=avg_rating)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
