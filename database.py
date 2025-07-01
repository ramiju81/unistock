import os
from flask import g
import psycopg2
from psycopg2.extras import DictCursor

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(
            os.environ.get('DATABASE_URL'),  # Usa la variable de entorno
            cursor_factory=DictCursor
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()