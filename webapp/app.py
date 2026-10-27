"""Gift idea list website.

Public, read-only lists live at /ideas/<slug>. Each person edits their own
list through a private /edit/<token> link that santa-helper-program.py emails
to them.
"""
import configparser
import os
import sys

from flask import Flask, abort, redirect, render_template, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import santa_db  # noqa: E402

MAX_TITLE = 200
MAX_URL = 2000
MAX_DESCRIPTION = 2000


def cleanUrl(url):
    """Returns a safe http(s) URL, '' for no URL, or None if it isn't allowed."""
    url = url.strip()
    if url == '':
        return ''
    if '://' not in url:
        url = 'https://' + url
    scheme = url.split('://', 1)[0].lower()
    if scheme not in ('http', 'https') or len(url) > MAX_URL or any(c.isspace() for c in url):
        return None
    return url


def readItemForm(form):
    """Returns (fields, error) for an add/edit form submission."""
    title = form.get('title', '').strip()
    description = form.get('description', '').strip()
    url = cleanUrl(form.get('url', ''))
    if title == '':
        return None, 'Please give the item a title.'
    if len(title) > MAX_TITLE or len(description) > MAX_DESCRIPTION:
        return None, 'That title or description is too long.'
    if url is None:
        return None, 'Links need to be normal web addresses (http:// or https://).'
    return {'title': title, 'url': url, 'description': description}, None


def dbPathFromConfig():
    confPath = os.environ.get('SANTA_CONF', 'santa.conf')
    config = configparser.ConfigParser()
    config.read(confPath)
    dbFile = config.get('email data', 'dbFile', fallback='santa.db')
    if not os.path.isabs(dbFile):
        dbFile = os.path.join(os.path.dirname(os.path.abspath(confPath)), dbFile)
    return dbFile


def create_app(dbPath=None):
    app = Flask(__name__)
    # Trust the reverse proxy (nginx/Caddy) for the real host and https scheme.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    app.config['DB_PATH'] = dbPath or dbPathFromConfig()
    santa_db.init_db(app.config['DB_PATH'])

    def db():
        return app.config['DB_PATH']

    def personForToken(token):
        person = santa_db.get_person_by_token(db(), token)
        if person is None:
            abort(404)
        return person

    def renderEdit(person, error=None, form=None, status=200):
        items = santa_db.list_items(db(), person['id'])
        return render_template('edit.html', person=person, items=items, error=error,
                               form=form or {}), status

    @app.after_request
    def headers(response):
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.route('/')
    def home():
        return redirect(url_for('index'))

    @app.route('/ideas/')
    def index():
        return render_template('index.html', people=santa_db.list_people(db()))

    @app.route('/ideas/<slug>')
    def view(slug):
        person = santa_db.get_person_by_slug(db(), slug)
        if person is None:
            abort(404)
        return render_template('view.html', person=person, items=santa_db.list_items(db(), person['id']))

    @app.route('/edit/<token>')
    def edit(token):
        return renderEdit(personForToken(token))

    @app.route('/edit/<token>/add', methods=['POST'])
    def add(token):
        person = personForToken(token)
        fields, error = readItemForm(request.form)
        if error:
            return renderEdit(person, error, request.form, 400)
        santa_db.add_item(db(), person['id'], **fields)
        return redirect(url_for('edit', token=token))

    @app.route('/edit/<token>/item/<int:itemId>/edit', methods=['POST'])
    def update(token, itemId):
        person = personForToken(token)
        fields, error = readItemForm(request.form)
        if error:
            return renderEdit(person, error, status=400)
        if not santa_db.update_item(db(), person['id'], itemId, **fields):
            abort(404)
        return redirect(url_for('edit', token=token))

    @app.route('/edit/<token>/item/<int:itemId>/delete', methods=['POST'])
    def delete(token, itemId):
        person = personForToken(token)
        if not santa_db.delete_item(db(), person['id'], itemId):
            abort(404)
        return redirect(url_for('edit', token=token))

    @app.errorhandler(404)
    def notFound(error):
        return render_template('404.html'), 404

    return app


if __name__ == '__main__':
    create_app().run(debug=True)
