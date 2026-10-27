import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import santa_db  # noqa: E402
from webapp.app import cleanUrl, create_app  # noqa: E402


@pytest.fixture
def setup(tmp_path):
    path = str(tmp_path / 'santa.db')
    santa_db.sync_people(path, ['Alice', 'Bob'], ['a@x.com', 'b@x.com'])
    client = create_app(path).test_client()
    alice = santa_db.get_person_by_name(path, 'Alice')
    bob = santa_db.get_person_by_name(path, 'Bob')
    return path, client, alice, bob


def test_clean_url():
    assert cleanUrl('') == ''
    assert cleanUrl('amazon.com/socks') == 'https://amazon.com/socks'
    assert cleanUrl('http://x.com') == 'http://x.com'
    # No "://", so it gets https:// put in front and becomes a harmless web link.
    assert cleanUrl('javascript:alert(1)') == 'https://javascript:alert(1)'
    assert cleanUrl('javascript://alert(1)') is None
    assert cleanUrl('data://text/html,hi') is None


def test_add_and_view(setup):
    path, client, alice, bob = setup
    response = client.post('/edit/{}/add'.format(alice['edit_token']),
                           data={'title': 'Lego <set>', 'url': 'lego.com/x', 'description': 'The big one'})
    assert response.status_code == 302
    page = client.get('/ideas/alice').get_data(as_text=True)
    assert 'Lego &lt;set&gt;' in page
    assert 'href="https://lego.com/x"' in page
    assert alice['edit_token'] not in page
    assert '/edit/' not in page


def test_title_required(setup):
    path, client, alice, bob = setup
    response = client.post('/edit/{}/add'.format(alice['edit_token']), data={'title': '  '})
    assert response.status_code == 400
    assert santa_db.list_items(path, alice['id']) == []


def test_bad_url_rejected(setup):
    path, client, alice, bob = setup
    response = client.post('/edit/{}/add'.format(alice['edit_token']),
                           data={'title': 'x', 'url': 'javascript://alert(1)'})
    assert response.status_code == 400
    assert santa_db.list_items(path, alice['id']) == []


def test_cannot_touch_someone_elses_item(setup):
    path, client, alice, bob = setup
    itemId = santa_db.add_item(path, bob['id'], 'Bike')
    assert client.post('/edit/{}/item/{}/delete'.format(alice['edit_token'], itemId)).status_code == 404
    assert client.post('/edit/{}/item/{}/edit'.format(alice['edit_token'], itemId),
                       data={'title': 'Hacked'}).status_code == 404
    assert santa_db.list_items(path, bob['id'])[0]['title'] == 'Bike'


def test_edit_and_delete_own_item(setup):
    path, client, alice, bob = setup
    itemId = santa_db.add_item(path, alice['id'], 'Book')
    client.post('/edit/{}/item/{}/edit'.format(alice['edit_token'], itemId), data={'title': 'Two books'})
    assert santa_db.list_items(path, alice['id'])[0]['title'] == 'Two books'
    client.post('/edit/{}/item/{}/delete'.format(alice['edit_token'], itemId))
    assert santa_db.list_items(path, alice['id']) == []


def test_not_found(setup):
    path, client, alice, bob = setup
    assert client.get('/ideas/nobody').status_code == 404
    assert client.get('/edit/not-a-token').status_code == 404
    assert client.post('/edit/not-a-token/add', data={'title': 'x'}).status_code == 404
