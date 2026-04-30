from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3, os, hashlib, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'shopzone-secret-key-2025'
DATABASE = os.environ.get('DATABASE_PATH', '/data/shopzone.db')

# ── DB helpers ──────────────────────────────────────────────────────────────
def get_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

# ── Init DB + seed ───────────────────────────────────────────────────────────
def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            original_price REAL,
            description TEXT,
            image_emoji TEXT,
            badge TEXT,
            rating REAL DEFAULT 4.5,
            reviews INTEGER DEFAULT 100,
            in_stock INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL
        );
    ''')
    # Seed products only if empty
    count = db.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    if count == 0:
        products = [
            # Phones
            ('iPhone 15 Pro Max', 'phones', 134900, 149900, '6.7" Super Retina XDR, A17 Pro chip, 48MP camera', '📱', 'HOT', 4.8, 2341, 1),
            ('Samsung Galaxy S24 Ultra', 'phones', 124999, 139999, '6.8" Dynamic AMOLED, Snapdragon 8 Gen 3, 200MP', '📱', 'SALE', 4.7, 1876, 1),
            ('OnePlus 12', 'phones', 64999, 74999, '6.82" LTPO AMOLED, Snapdragon 8 Gen 3, 50MP Hasselblad', '📱', 'NEW', 4.6, 987, 1),
            ('Google Pixel 8 Pro', 'phones', 84999, 99999, '6.7" LTPO OLED, Google Tensor G3, 50MP wide', '📱', 'SALE', 4.7, 654, 1),
            ('Xiaomi 14 Ultra', 'phones', 89999, 99999, '6.73" LTPO AMOLED, Snapdragon 8 Gen 3, Leica camera', '📱', None, 4.5, 432, 1),
            ('Nothing Phone 2a', 'phones', 23999, 27999, '6.7" AMOLED, Dimensity 7200 Pro, Glyph interface', '📱', 'BUDGET', 4.4, 765, 1),
            # Laptops
            ('MacBook Pro 14" M3 Pro', 'laptops', 199900, 219900, 'M3 Pro chip, 18GB RAM, 512GB SSD, Liquid Retina XDR', '💻', 'HOT', 4.9, 1234, 1),
            ('Dell XPS 15', 'laptops', 149990, 169990, 'Intel Core i7-13700H, RTX 4060, 16GB RAM, 512GB SSD', '💻', 'SALE', 4.7, 876, 1),
            ('ASUS ROG Zephyrus G14', 'laptops', 119990, 134990, 'AMD Ryzen 9, RTX 4060, 16GB, 1TB, 2.5K 165Hz', '💻', 'GAMING', 4.8, 654, 1),
            ('HP Spectre x360', 'laptops', 139990, 154990, 'Intel Core i7, Intel Iris Xe, 16GB RAM, OLED touch', '💻', None, 4.6, 432, 1),
            ('Lenovo ThinkPad X1 Carbon', 'laptops', 129990, 149990, 'Intel Core i7, 16GB, 512GB, 14" IPS anti-glare', '💻', 'BUSINESS', 4.7, 543, 1),
            ('Acer Predator Helios 16', 'laptops', 139990, 159990, 'Intel i9 13th Gen, RTX 4070, 32GB, 1TB, 240Hz', '💻', 'GAMING', 4.8, 321, 1),
            # Gaming Consoles
            ('PlayStation 5 Slim', 'gaming', 44990, 54990, 'PS5 Slim disc edition, 1TB SSD, 4K gaming, DualSense', '🎮', 'HOT', 4.9, 3421, 1),
            ('Xbox Series X', 'gaming', 52990, 59990, '12 teraflops, 1TB NVMe SSD, 4K/120fps, Game Pass', '🎮', 'SALE', 4.8, 2134, 1),
            ('Nintendo Switch OLED', 'gaming', 29990, 34990, '7" OLED screen, 64GB storage, enhanced audio', '🎮', None, 4.7, 4321, 1),
            ('Steam Deck OLED', 'gaming', 54990, 59990, '7.4" HDR OLED, AMD APU, 512GB, PC gaming portable', '🎮', 'NEW', 4.8, 1234, 1),
            ('PS5 DualSense Controller', 'gaming', 5990, 6990, 'Haptic feedback, adaptive triggers, built-in mic', '🎮', None, 4.8, 5432, 1),
            ('Xbox Elite Controller Series 2', 'gaming', 13990, 15990, 'Adjustable tension thumbsticks, wrap-around rubberized grip', '🎮', None, 4.7, 2341, 1),
            # AirPods & Earbuds
            ('AirPods Pro 2nd Gen', 'airpods', 24900, 29900, 'Active Noise Cancellation, Adaptive Transparency, H2 chip', '🎧', 'HOT', 4.8, 4321, 1),
            ('AirPods 3rd Generation', 'airpods', 17900, 19900, 'Spatial Audio, Adaptive EQ, Lightning charging case', '🎧', None, 4.6, 2134, 1),
            ('Sony WF-1000XM5', 'airpods', 19990, 24990, 'Industry-leading ANC, 8hr battery, LDAC Hi-Res Audio', '🎧', 'SALE', 4.8, 1876, 1),
            ('Samsung Galaxy Buds 2 Pro', 'airpods', 14999, 17999, '360 Audio, ANC, Hi-Fi sound, IPX7 water resistant', '🎧', None, 4.6, 987, 1),
            ('Bose QuietComfort Earbuds II', 'airpods', 21990, 26990, 'CustomTune sound calibration, 6hr battery, IPX4', '🎧', 'PREMIUM', 4.7, 654, 1),
            ('Nothing Ear 2', 'airpods', 8999, 10999, '11.6mm driver, LHDC 5.0, ANC, 36hr total battery', '🎧', 'BUDGET', 4.5, 1234, 1),
            # iPads & Tablets
            ('iPad Pro 12.9" M2', 'tablets', 112900, 124900, 'M2 chip, Liquid Retina XDR, Thunderbolt, Wi-Fi 6E', '📲', 'HOT', 4.9, 1543, 1),
            ('iPad Air 5th Gen', 'tablets', 59900, 69900, 'M1 chip, 10.9" Liquid Retina, 5G, USB-C, Touch ID', '📲', 'SALE', 4.8, 2134, 1),
            ('iPad 10th Generation', 'tablets', 44900, 49900, 'A14 Bionic, 10.9" Liquid Retina, Wi-Fi 6, USB-C', '📲', None, 4.7, 3211, 1),
            ('Samsung Galaxy Tab S9 Ultra', 'tablets', 107999, 119999, '14.6" Dynamic AMOLED, Snapdragon 8 Gen 2, 12GB RAM', '📲', 'ANDROID', 4.7, 765, 1),
            ('Microsoft Surface Pro 9', 'tablets', 119990, 134990, 'Intel Core i5/i7, 13" PixelSense Flow, 2-in-1 design', '📲', None, 4.6, 432, 1),
            # Accessories
            ('Apple Watch Series 9', 'accessories', 41900, 45900, 'S9 chip, Always-On Retina, ECG, Blood Oxygen, GPS', '⌚', 'HOT', 4.8, 2134, 1),
            ('Samsung Galaxy Watch 6', 'accessories', 24999, 29999, '1.5" Super AMOLED, BioActive sensor, Wear OS', '⌚', None, 4.6, 987, 1),
            ('Apple MagSafe Charger', 'accessories', 3900, 4500, '15W MagSafe charging for iPhone 12 and later', '🔌', None, 4.5, 5432, 1),
            ('Anker 65W USB-C Charger', 'accessories', 2499, 3499, 'GaN technology, 3 ports, foldable plug, fast charge', '🔌', 'BUDGET', 4.7, 4321, 1),
        ]
        db.executemany(
            'INSERT INTO products (name,category,price,original_price,description,image_emoji,badge,rating,reviews,in_stock) VALUES (?,?,?,?,?,?,?,?,?,?)',
            products
        )
    db.commit()
    db.close()

init_db()

# ── Auth routes ──────────────────────────────────────────────────────────────
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        name  = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        pw    = request.form['password']
        if len(pw) < 6:
            flash('Password must be at least 6 characters', 'error')
            return redirect(url_for('signup'))
        db = get_db()
        try:
            db.execute('INSERT INTO users (name,email,password) VALUES (?,?,?)',
                       (name, email, hash_pw(pw)))
            db.commit()
            user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            flash(f'Welcome to ShopZone, {name}!', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('Email already registered. Please login.', 'error')
        finally:
            db.close()
    return render_template('auth.html', mode='signup')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        pw    = request.form['password']
        db    = get_db()
        user  = db.execute('SELECT * FROM users WHERE email=? AND password=?',
                           (email, hash_pw(pw))).fetchone()
        db.close()
        if user:
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('index'))
        flash('Invalid email or password', 'error')
    return render_template('auth.html', mode='login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ── Main pages ───────────────────────────────────────────────────────────────
@app.route('/')
def index():
    db = get_db()
    offers    = db.execute("SELECT * FROM products WHERE badge IN ('HOT','SALE') LIMIT 6").fetchall()
    phones    = db.execute("SELECT * FROM products WHERE category='phones' LIMIT 4").fetchall()
    laptops   = db.execute("SELECT * FROM products WHERE category='laptops' LIMIT 4").fetchall()
    gaming    = db.execute("SELECT * FROM products WHERE category='gaming' LIMIT 4").fetchall()
    airpods   = db.execute("SELECT * FROM products WHERE category='airpods' LIMIT 4").fetchall()
    tablets   = db.execute("SELECT * FROM products WHERE category='tablets' LIMIT 4").fetchall()
    cart_count = 0
    if session.get('user_id'):
        cart_count = db.execute('SELECT SUM(quantity) FROM cart WHERE user_id=?',
                                (session['user_id'],)).fetchone()[0] or 0
    db.close()
    return render_template('index.html', offers=offers, phones=phones,
                           laptops=laptops, gaming=gaming, airpods=airpods,
                           tablets=tablets, cart_count=cart_count)

@app.route('/category/<cat>')
def category(cat):
    db = get_db()
    sort = request.args.get('sort', 'default')
    order = {'price_asc': 'price ASC', 'price_desc': 'price DESC',
             'rating': 'rating DESC', 'default': 'id ASC'}.get(sort, 'id ASC')
    products = db.execute(f'SELECT * FROM products WHERE category=? ORDER BY {order}', (cat,)).fetchall()
    cart_count = 0
    if session.get('user_id'):
        cart_count = db.execute('SELECT SUM(quantity) FROM cart WHERE user_id=?',
                                (session['user_id'],)).fetchone()[0] or 0
    db.close()
    cat_names = {'phones':'Smartphones','laptops':'Laptops','gaming':'Gaming Consoles',
                 'airpods':'Earbuds & AirPods','tablets':'iPads & Tablets','accessories':'Accessories'}
    return render_template('category.html', products=products, cat=cat,
                           cat_name=cat_names.get(cat, cat.title()),
                           sort=sort, cart_count=cart_count)

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    db = get_db()
    products = db.execute(
        "SELECT * FROM products WHERE name LIKE ? OR description LIKE ? OR category LIKE ?",
        (f'%{q}%', f'%{q}%', f'%{q}%')
    ).fetchall() if q else []
    cart_count = 0
    if session.get('user_id'):
        cart_count = db.execute('SELECT SUM(quantity) FROM cart WHERE user_id=?',
                                (session['user_id'],)).fetchone()[0] or 0
    db.close()
    return render_template('search.html', products=products, q=q, cart_count=cart_count)

# ── Cart ─────────────────────────────────────────────────────────────────────
@app.route('/cart/add/<int:pid>', methods=['POST'])
def add_to_cart(pid):
    if not session.get('user_id'):
        flash('Please login to add items to cart', 'error')
        return redirect(url_for('login'))
    db = get_db()
    existing = db.execute('SELECT * FROM cart WHERE user_id=? AND product_id=?',
                          (session['user_id'], pid)).fetchone()
    if existing:
        db.execute('UPDATE cart SET quantity=quantity+1 WHERE id=?', (existing['id'],))
    else:
        db.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?,?,1)',
                   (session['user_id'], pid))
    db.commit()
    db.close()
    flash('Item added to cart!', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/cart')
def cart():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    db = get_db()
    items = db.execute('''
        SELECT c.id, c.quantity, p.name, p.price, p.original_price,
               p.image_emoji, p.id as product_id
        FROM cart c JOIN products p ON c.product_id=p.id
        WHERE c.user_id=?
    ''', (session['user_id'],)).fetchall()
    total    = sum(i['price'] * i['quantity'] for i in items)
    cart_count = sum(i['quantity'] for i in items)
    db.close()
    return render_template('cart.html', items=items, total=total, cart_count=cart_count)

@app.route('/cart/remove/<int:cid>', methods=['POST'])
def remove_cart(cid):
    if not session.get('user_id'): return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM cart WHERE id=? AND user_id=?', (cid, session['user_id']))
    db.commit()
    db.close()
    return redirect(url_for('cart'))

@app.route('/cart/update/<int:cid>', methods=['POST'])
def update_cart(cid):
    if not session.get('user_id'): return redirect(url_for('login'))
    qty = int(request.form.get('quantity', 1))
    db  = get_db()
    if qty < 1:
        db.execute('DELETE FROM cart WHERE id=? AND user_id=?', (cid, session['user_id']))
    else:
        db.execute('UPDATE cart SET quantity=? WHERE id=? AND user_id=?',
                   (qty, cid, session['user_id']))
    db.commit()
    db.close()
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    if not session.get('user_id'): return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM cart WHERE user_id=?', (session['user_id'],))
    db.commit()
    db.close()
    flash('Order placed successfully! Thank you for shopping at ShopZone.', 'success')
    return redirect(url_for('index'))

# ── API ───────────────────────────────────────────────────────────────────────
@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat(), 'app': 'ShopZone'})

@app.route('/api/products')
def api_products():
    db = get_db()
    products = [dict(p) for p in db.execute('SELECT * FROM products').fetchall()]
    db.close()
    return jsonify(products)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
