import os

import psycopg2
import psycopg2.extras
from flask import g


DATABASE_URL = os.environ.get('postgres://root:857oq5STWMhCKnISy2mTZ1mJnjMfnwXe@localhost:5432/servicio_y6u5')


def get_db():
    if 'db' not in g:
        if not DATABASE_URL:
            raise RuntimeError(
                'DATABASE_URL environment variable must be defined for PostgreSQL connections'
            )
        g.db = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        g.db.autocommit = False
    return g.db


def get_cursor():
    return get_db().cursor()


def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()