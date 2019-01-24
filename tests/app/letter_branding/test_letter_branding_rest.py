import json

import pytest

from app.models import LetterBranding
from tests import create_authorization_header
from tests.app.db import create_letter_branding


def test_get_all_letter_brands(client, notify_db_session):
    platform_default = create_letter_branding()
    test_domain_branding = create_letter_branding(
        name='test domain', filename='test-domain', domain='test.domain', platform_default=False
    )
    response = client.get('/letter-branding', headers=[create_authorization_header()])
    assert response.status_code == 200
    json_response = json.loads(response.get_data(as_text=True))
    assert len(json_response) == 2
    for brand in json_response:
        if brand['id'] == platform_default:
            platform_default.serialize() == brand
        else:
            test_domain_branding.serialize() == brand


def test_create_letter_branding(client, notify_db_session):
    form = {
        'name': 'super brand',
        'domain': 'super.brand',
        'filename': 'super-brand'
    }

    response = client.post(
        '/letter-branding',
        data=json.dumps(form),
        headers=[('Content-Type', 'application/json'), create_authorization_header()],
    )

    assert response.status_code == 201
    json_response = json.loads(response.get_data(as_text=True))
    letter_brand = LetterBranding.query.get(json_response['id'])
    assert letter_brand.name == form['name']
    assert letter_brand.domain == form['domain']
    assert letter_brand.filename == form['filename']
    assert not letter_brand.platform_default


def test_create_letter_branding_returns_400_if_platform_default_is_passed_in_the_form(client, notify_db_session):
    form = {
        'name': 'super brand',
        'domain': 'super.brand',
        'filename': 'super-brand',
        'platform_default': True
    }

    response = client.post(
        '/letter-branding',
        data=json.dumps(form),
        headers=[('Content-Type', 'application/json'), create_authorization_header()],
    )
    assert response.status_code == 400
    json_resp = json.loads(response.get_data(as_text=True))
    assert json_resp['errors'][0]['message'] == \
        "Additional properties are not allowed (platform_default was unexpected)"


def test_create_letter_branding_returns_400_if_name_already_exists(client, notify_db_session):
    create_letter_branding(name='duplicate', domain='duplicate', filename='duplicate')
    form = {
        'name': 'duplicate',
        'domain': 'super.brand',
        'filename': 'super-brand',
    }

    response = client.post(
        '/letter-branding',
        headers=[('Content-Type', 'application/json'), create_authorization_header()],
        data=json.dumps(form)
    )

    assert response.status_code == 400
    json_resp = json.loads(response.get_data(as_text=True))
    assert json_resp['message'] == {'name': ["Duplicate domain 'super.brand'"]}


def test_update_letter_branding_returns_400_when_integrity_error_is_thrown(
        client, notify_db_session
):
    create_letter_branding(name='duplicate', domain='duplicate', filename='duplicate')
    brand_to_update = create_letter_branding(name='super brand', domain='super brand', filename='super brand')
    form = {
        'name': 'super brand',
        'domain': 'duplicate',
        'filename': 'super-brand',
    }

    response = client.post(
        '/letter-branding/{}'.format(brand_to_update.id),
        headers=[('Content-Type', 'application/json'), create_authorization_header()],
        data=json.dumps(form)
    )

    assert response.status_code == 400
    json_resp = json.loads(response.get_data(as_text=True))
    # Why is this name and not domain? copied this pattern from email_branding
    assert json_resp['message'] == {"name": ["Duplicate domain 'duplicate'"]}
