import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import santa_db  # noqa: E402


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / 'santa.db')
    santa_db.sync_people(path, ['Sarah Smith', 'Bob', 'sarah smith!'], ['s@x.com', 'b@x.com', 's2@x.com'])
    return path


def test_slugify():
    assert santa_db.slugify('Sarah Smith') == 'sarah-smith'
    assert santa_db.slugify("  O'Neil  ") == 'o-neil'
    assert santa_db.slugify('!!!') == 'person'


def test_slug_collisions_get_suffix(db):
    slugs = {p['name']: p['slug'] for p in santa_db.list_people(db)}
    assert slugs['Sarah Smith'] == 'sarah-smith'
    assert slugs['sarah smith!'] == 'sarah-smith-2'


def test_sync_is_idempotent_and_keeps_links(db):
    before = santa_db.get_person_by_name(db, 'Bob')
    santa_db.sync_people(db, ['Bob', 'Carol'], ['bob@new.com', 'c@x.com'])
    after = santa_db.get_person_by_name(db, 'Bob')
    assert after['edit_token'] == before['edit_token']
    assert after['slug'] == before['slug']
    assert after['email'] == 'bob@new.com'
    assert len(santa_db.list_people(db)) == 4


def test_rotate_token(db):
    old = santa_db.get_person_by_name(db, 'Bob')['edit_token']
    new = santa_db.rotate_token(db, 'Bob')
    assert new != old
    assert santa_db.get_person_by_token(db, old) is None
    with pytest.raises(KeyError):
        santa_db.rotate_token(db, 'Nobody')


def test_items_scoped_to_owner(db):
    bob = santa_db.get_person_by_name(db, 'Bob')
    sarah = santa_db.get_person_by_name(db, 'Sarah Smith')
    itemId = santa_db.add_item(db, bob['id'], 'Socks')
    assert not santa_db.update_item(db, sarah['id'], itemId, 'Hacked')
    assert not santa_db.delete_item(db, sarah['id'], itemId)
    assert santa_db.list_items(db, bob['id'])[0]['title'] == 'Socks'
    assert santa_db.update_item(db, bob['id'], itemId, 'Wool socks', 'https://x.com', 'Size L')
    assert santa_db.delete_item(db, bob['id'], itemId)
    assert santa_db.list_items(db, bob['id']) == []
