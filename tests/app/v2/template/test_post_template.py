import pytest
import uuid

from flask import json

from app.models import EMAIL_TYPE, SMS_TYPE, LETTER_TYPE
from tests import create_authorization_header
from tests.app.db import create_template

valid_data = {
    'personalisation': {'Name': 'Jo'}
}


@pytest.mark.parametrize("tmp_type", [EMAIL_TYPE, SMS_TYPE])
def test_valid_post_template_returns_200(client, sample_service, tmp_type):
    template = create_template(
        sample_service,
        template_type=tmp_type,
        content='Dear ((Name)), Hello. Yours Truly, The Government.')

    auth_header = create_authorization_header(service_id=sample_service.id)

    response = client.post(
        path='/v2/template/{}/preview'.format(template.id),
        data=json.dumps(valid_data),
        headers=[('Content-Type', 'application/json'), auth_header])

    assert response.status_code == 200

    resp_json = json.loads(response.get_data(as_text=True))

    assert resp_json['id'] == str(template.id)
    assert 'v2/template/{}/preview'.format(template.id) in resp_json['uri']
    assert 'Dear {}'.format(valid_data['personalisation']['Name']) in resp_json['content']['body']


@pytest.mark.parametrize("tmp_type", [EMAIL_TYPE, SMS_TYPE])
def test_invalid_post_template_returns_400(client, sample_service, tmp_type):
    template = create_template(
        sample_service,
        template_type=tmp_type,
        content='Dear ((Name)), Hello ((Missing)). Yours Truly, The Government.')

    auth_header = create_authorization_header(service_id=sample_service.id)

    response = client.post(
        path='/v2/template/{}/preview'.format(template.id),
        data=json.dumps(valid_data),
        headers=[('Content-Type', 'application/json'), auth_header])

    assert response.status_code == 400

    resp_json = json.loads(response.get_data(as_text=True))

    assert resp_json['errors'][0]['error'] == 'BadRequestError'
    assert 'Missing personalisation: Missing' in resp_json['errors'][0]['message']


def test_post_template_with_non_existent_template_id_returns_404(client, sample_service):
    auth_header = create_authorization_header(service_id=sample_service.id)

    random_template_id = str(uuid.uuid4())

    response = client.post(
        path='/v2/template/{}/preview'.format(random_template_id),
        data=json.dumps(valid_data),
        headers=[('Content-Type', 'application/json'), auth_header])

    assert response.status_code == 404
    assert response.headers['Content-type'] == 'application/json'

    json_response = json.loads(response.get_data(as_text=True))

    assert json_response == {
        "errors": [
            {
                "error": "NoResultFound",
                "message": "No result found"
            }
        ],
        "status_code": 404
    }
