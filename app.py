# app.py - Sistema Completo de Gestión de Inventario

import os
from flask import Flask, render_template, request, redirect, url_for, flash, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
from datetime import datetime, timedelta

# =============================================
# CONFIGURACIÓN INICIAL
# =============================================
load_dotenv()
app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['DATABASE_URL'] = os.getenv('DATABASE_URL', 'postgresql://postgres:8108@localhost:5432/customer')
# Asegúrate de que la URL de la base de datos sea correcta
#app.config['DATABASE_URL'] = os.getenv('DATABASE_URL', 'postgresql://usuario:contraseña@localhost:5432/unistock')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# =============================================
# AUTENTICACIÓN
# =============================================
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, email, phone=None, avatar_url=None):
        self.id = id
        self.username = username
        self.email = email
        self.phone = phone
        self.avatar_url = avatar_url

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        if user:
            return User(
                id=user['id'],
                username=user['username'],
                email=user['email'],
                phone=user.get('phone'),
                avatar_url=user.get('avatar_url')
            )
        return None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None
    finally:
        cursor.close()

# =============================================
# BASE DE DATOS
# =============================================
def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(
            app.config['DATABASE_URL'],
            cursor_factory=DictCursor
        )
    return g.db

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(20),
                avatar_url VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL,
                cost DECIMAL(10, 2),
                stock INTEGER NOT NULL DEFAULT 0,
                min_stock INTEGER NOT NULL DEFAULT 5,
                barcode VARCHAR(50),
                category VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS customers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                identification VARCHAR(50) NOT NULL,
                phone VARCHAR(20),
                email VARCHAR(100),
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS suppliers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                tax_id VARCHAR(50) NOT NULL,
                contact_person VARCHAR(100),
                phone VARCHAR(20),
                email VARCHAR(100),
                products TEXT,
                address TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS sales (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER REFERENCES customers(id),
                date TIMESTAMP NOT NULL,
                total DECIMAL(10, 2) NOT NULL,
                payment_method VARCHAR(50) NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS sale_items (
                id SERIAL PRIMARY KEY,
                sale_id INTEGER REFERENCES sales(id),
                product_id INTEGER REFERENCES products(id),
                quantity INTEGER NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                subtotal DECIMAL(10, 2) NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS purchases (
                id SERIAL PRIMARY KEY,
                supplier_id INTEGER REFERENCES suppliers(id),
                date TIMESTAMP NOT NULL,
                total DECIMAL(10, 2) NOT NULL,
                payment_method VARCHAR(50) NOT NULL,
                invoice_number VARCHAR(50),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS purchase_items (
                id SERIAL PRIMARY KEY,
                purchase_id INTEGER REFERENCES purchases(id),
                product_id INTEGER REFERENCES products(id),
                quantity INTEGER NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                subtotal DECIMAL(10, 2) NOT NULL
            );
        """)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        raise
    finally:
        cursor.close()

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# =============================================
# FUNCIONES AUXILIARES
# =============================================
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

# =============================================
# RUTAS DE AUTENTICACIÓN
# =============================================
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            
            if user and bcrypt.check_password_hash(user['password'], password):
                user_obj = User(
                    id=user['id'],
                    username=user['username'],
                    email=user['email'],
                    phone=user.get('phone'),
                    avatar_url=user.get('avatar_url')
                )
                login_user(user_obj)
                return redirect(url_for('dashboard'))
            
            flash('Credenciales incorrectas', 'error')
        except Exception as e:
            flash('Error al iniciar sesión', 'error')
            print(f"Login error: {e}")
        finally:
            cursor.close()
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return redirect(url_for('register'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                (username, email, hashed_password)
            )
            conn.commit()
            flash('Registro exitoso. Por favor inicie sesión.', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            flash('El usuario o email ya existen', 'error')
            conn.rollback()
        except Exception as e:
            flash('Error en el registro', 'error')
            print(f"Registration error: {e}")
            conn.rollback()
        finally:
            cursor.close()
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# =============================================
# RUTAS PRINCIPALES
# =============================================
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Estadísticas para el dashboard
        cursor.execute('SELECT COUNT(*) FROM products')
        product_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM customers')
        customer_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM suppliers')
        supplier_count = cursor.fetchone()[0]
        
        # Ventas de los últimos 7 días
        cursor.execute("""
            SELECT COALESCE(SUM(total), 0) 
            FROM sales 
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
        """)
        weekly_sales = cursor.fetchone()[0]
        
        # Productos con bajo stock
        cursor.execute("""
            SELECT name, stock 
            FROM products 
            WHERE stock <= min_stock 
            ORDER BY stock ASC 
            LIMIT 5
        """)
        low_stock = cursor.fetchall()
        
        return render_template(
            'dashboard.html',
            product_count=product_count,
            customer_count=customer_count,
            supplier_count=supplier_count,
            weekly_sales=weekly_sales,
            low_stock=low_stock
        )
    except Exception as e:
        flash('Error al cargar el dashboard', 'error')
        print(f"Dashboard error: {e}")
        return redirect(url_for('login'))
    finally:
        cursor.close()

@app.route('/products')
@login_required
def products():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM products ORDER BY name')
        products = cursor.fetchall()
        return render_template('products.html', products=products)
    except Exception as e:
        flash('Error al cargar productos', 'error')
        print(f"Products error: {e}")
        return redirect(url_for('dashboard'))
    finally:
        cursor.close()

@app.route('/customers')
@login_required
def customers():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM customers ORDER BY name')
        customers = cursor.fetchall()
        return render_template('customers.html', customers=customers)
    except Exception as e:
        flash('Error al cargar clientes', 'error')
        print(f"Customers error: {e}")
        return redirect(url_for('dashboard'))
    finally:
        cursor.close()

@app.route('/purchases')
@login_required
def purchases():
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Obtener compras con información de proveedores
        cursor.execute("""
            SELECT p.*, s.name as supplier_name 
            FROM purchases p
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            ORDER BY p.date DESC
        """)
        purchases = cursor.fetchall()
        
        # Obtener items para cada compra
        for purchase in purchases:
            cursor.execute("""
                SELECT pi.*, pr.name as product_name 
                FROM purchase_items pi
                JOIN products pr ON pi.product_id = pr.id
                WHERE pi.purchase_id = %s
            """, (purchase['id'],))
            purchase['items'] = cursor.fetchall()
        
        # Obtener proveedores y productos para el formulario
        cursor.execute('SELECT * FROM suppliers ORDER BY name')
        suppliers = cursor.fetchall()
        
        cursor.execute('SELECT * FROM products ORDER BY name')
        products = cursor.fetchall()
        
        return render_template('purchases.html', 
                            purchases=purchases,
                            suppliers=suppliers,
                            products=products,
                            today=datetime.now().strftime('%Y-%m-%d'))
    except Exception as e:
        flash('Error al cargar compras', 'error')
        print(f"Purchases error: {e}")
        return redirect(url_for('dashboard'))
    finally:
        cursor.close()

# =============================================
# MANEJO DE ERRORES
# =============================================
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

# =============================================
# INICIALIZACIÓN
# =============================================
app.teardown_appcontext(close_db)

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=8000, debug=True)