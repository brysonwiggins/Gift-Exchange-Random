"""Shared SQLite storage for the gift idea lists.

Used by both santa-helper-program.py (to create people and links) and the
web app in webapp/ (to show and edit the lists).
"""
import re
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL DEFAULT '',
    edit_token TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    url TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS items_person ON items(person_id);
"""


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db(path):
    with closing(connect(path)) as conn, conn:
        conn.executescript(SCHEMA)


def newToken():
    return secrets.token_urlsafe(16)


def slugify(name):
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug or 'person'


def uniqueSlug(conn, name):
    base = slugify(name)
    slug = base
    suffix = 2
    while conn.execute('SELECT 1 FROM people WHERE slug = ?', (slug,)).fetchone():
        slug = '{base}-{n}'.format(base=base, n=suffix)
        suffix += 1
    return slug


def sync_people(path, names, emails):
    """Make sure everyone in the exchange list has a row, a slug and an edit token.

    Existing people keep their slug and token so links stay the same every year.
    """
    init_db(path)
    with closing(connect(path)) as conn, conn:
        for name, email in zip(names, emails):
            row = conn.execute('SELECT id, email FROM people WHERE name = ?', (name,)).fetchone()
            if row is None:
                conn.execute('INSERT INTO people (name, slug, email, edit_token) VALUES (?, ?, ?, ?)',
                             (name, uniqueSlug(conn, name), email, newToken()))
            elif row['email'] != email:
                conn.execute('UPDATE people SET email = ? WHERE id = ?', (email, row['id']))


def rotate_token(path, name):
    with closing(connect(path)) as conn, conn:
        token = newToken()
        cursor = conn.execute('UPDATE people SET edit_token = ? WHERE name = ?', (token, name))
        if cursor.rowcount == 0:
            raise KeyError(name)
        return token


def _one(path, query, args):
    with closing(connect(path)) as conn:
        row = conn.execute(query, args).fetchone()
        return dict(row) if row else None


def get_person_by_slug(path, slug):
    return _one(path, 'SELECT * FROM people WHERE slug = ?', (slug,))


def get_person_by_token(path, token):
    return _one(path, 'SELECT * FROM people WHERE edit_token = ?', (token,))


def get_person_by_name(path, name):
    return _one(path, 'SELECT * FROM people WHERE name = ?', (name,))


def list_people(path):
    with closing(connect(path)) as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM people ORDER BY name COLLATE NOCASE')]


def list_items(path, personId):
    with closing(connect(path)) as conn:
        rows = conn.execute('SELECT * FROM items WHERE person_id = ? ORDER BY id', (personId,))
        return [dict(row) for row in rows]


def add_item(path, personId, title, url='', description=''):
    with closing(connect(path)) as conn, conn:
        cursor = conn.execute(
            'INSERT INTO items (person_id, title, url, description, created_at) VALUES (?, ?, ?, ?, ?)',
            (personId, title, url, description, datetime.now().isoformat(timespec='seconds')))
        return cursor.lastrowid


def update_item(path, personId, itemId, title, url='', description=''):
    """Returns False when the item doesn't exist or belongs to someone else."""
    with closing(connect(path)) as conn, conn:
        cursor = conn.execute(
            'UPDATE items SET title = ?, url = ?, description = ? WHERE id = ? AND person_id = ?',
            (title, url, description, itemId, personId))
        return cursor.rowcount == 1


def delete_item(path, personId, itemId):
    """Returns False when the item doesn't exist or belongs to someone else."""
    with closing(connect(path)) as conn, conn:
        cursor = conn.execute('DELETE FROM items WHERE id = ? AND person_id = ?', (itemId, personId))
        return cursor.rowcount == 1
