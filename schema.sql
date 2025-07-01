-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    email TEXT NOT NULL,
    full_name TEXT,
    phone TEXT,
    avatar TEXT,
    reset_token TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    business_address TEXT,
    alternate_address TEXT
);

-- Tabla de productos
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC NOT NULL,
    stock INTEGER NOT NULL,
    min_stock INTEGER DEFAULT 0
);

-- Tabla de transacciones
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    type TEXT CHECK (type IN ('sale', 'entry')),
    quantity INTEGER NOT NULL,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
