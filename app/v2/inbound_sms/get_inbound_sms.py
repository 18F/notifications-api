import uuid

from flask import jsonify, request, url_for, current_app
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.exceptions import abort

from notifications_utils.recipients import validate_and_format_phone_number
from notifications_utils.recipients import InvalidPhoneError

from app import authenticated_service
from app.dao import inbound_sms_dao
from app.v2.errors import BadRequestError
from app.v2.inbound_sms import v2_inbound_sms_blueprint


@v2_inbound_sms_blueprint.route("/<user_number>", methods=['GET'])
def get_inbound_sms_by_number(user_number):
    _data = request.args.to_dict(flat=False)

    # flat=False makes everything a list, but we only ever allow one value for "older_than"
    if 'older_than' in _data:
        _data['older_than'] = _data['older_than'][0]

    try:
        user_number = validate_and_format_phone_number(user_number)
    except InvalidPhoneError as e:
        raise BadRequestError(message=str(e))

    paginated_inbound_sms = inbound_sms_dao.dao_get_paginated_inbound_sms_for_service(
        authenticated_service.id,
        user_number=user_number,
        older_than=_data.get('older_than'),
        page_size=current_app.config.get('API_PAGE_SIZE')
    )

    return jsonify(
        received_text_messages=[i.serialize() for i in paginated_inbound_sms],
        links=_build_links(
            paginated_inbound_sms,
            endpoint='get_inbound_sms_by_number',
            user_number=user_number
        )
    ), 200


@v2_inbound_sms_blueprint.route("", methods=['GET'])
def get_all_inbound_sms():
    _data = request.args.to_dict(flat=False)

    # flat=False makes everything a list, but we only ever allow one value for "older_than"
    if 'older_than' in _data:
        _data['older_than'] = _data['older_than'][0]

    paginated_inbound_sms = inbound_sms_dao.dao_get_paginated_inbound_sms_for_service(
        authenticated_service.id,
        older_than=_data.get('older_than'),
        page_size=current_app.config.get('API_PAGE_SIZE')
    )

    return jsonify(
        received_text_messages=[i.serialize() for i in paginated_inbound_sms],
        links=_build_links(paginated_inbound_sms, endpoint='get_all_inbound_sms')
    ), 200


def _build_links(inbound_sms_list, endpoint, user_number=None):
    _links = {
        'current': url_for(
            "v2_inbound_sms.{}".format(endpoint),
            user_number=user_number,
            _external=True,
        ),
    }

    if inbound_sms_list:
        _links['next'] = url_for(
            "v2_inbound_sms.{}".format(endpoint),
            user_number=user_number,
            older_than=inbound_sms_list[-1].id,
            _external=True,
        )

    return _links
