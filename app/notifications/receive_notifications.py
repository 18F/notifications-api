from urllib.parse import unquote

import iso8601
from flask import jsonify, Blueprint, current_app, request
from notifications_utils.recipients import normalise_phone_number

from app import statsd_client
from app.dao.services_dao import dao_fetch_services_by_sms_sender
from app.dao.inbound_sms_dao import dao_create_inbound_sms
from app.models import InboundSms
from app.errors import register_errors
from app.utils import convert_bst_to_utc

receive_notifications_blueprint = Blueprint('receive_notifications', __name__)
register_errors(receive_notifications_blueprint)


@receive_notifications_blueprint.route('/notifications/sms/receive/mmg', methods=['POST'])
def receive_mmg_sms():
    """
    {
        'MSISDN': '447123456789'
        'Number': '40604',
        'Message': 'some+uri+encoded+message%3A',
        'ID': 'SOME-MMG-SPECIFIC-ID',
        'DateRecieved': '2017-05-21+11%3A56%3A11'
    }
    """
    post_data = request.get_json()
    potential_services = dao_fetch_services_by_sms_sender(post_data['Number'])

    if len(potential_services) != 1:
        current_app.logger.error('Inbound number "{}" not associated with exactly one service'.format(
            post_data['Number']
        ))
        statsd_client.incr('inbound.mmg.failed')
        # since this is an issue with our service <-> number mapping, we should still tell MMG that we received
        # succesfully
        return 'RECEIVED', 200

    statsd_client.incr('inbound.mmg.succesful')

    service = potential_services[0]

    inbound = create_inbound_mmg_sms_object(service, post_data)

    current_app.logger.info('{} received inbound SMS with reference {}'.format(service.id, inbound.provider_reference))

    return 'RECEIVED', 200


def format_mmg_message(message):
    return unquote(message.replace('+', ' '))


def format_mmg_datetime(date):
    """
    We expect datetimes in format 2017-05-21+11%3A56%3A11 - ie, spaces replaced with pluses, and URI encoded
    (the same as UTC)
    """
    orig_date = format_mmg_message(date)
    parsed_datetime = iso8601.parse_date(orig_date).replace(tzinfo=None)
    return convert_bst_to_utc(parsed_datetime)


def create_inbound_mmg_sms_object(service, json):
    message = format_mmg_message(json['Message'])
    user_number = normalise_phone_number(json['MSISDN'])

    provider_date = json.get('DateRecieved')
    if provider_date:
        provider_date = format_mmg_datetime(provider_date)

    inbound = InboundSms(
        service=service,
        notify_number=service.sms_sender,
        user_number=user_number,
        provider_date=provider_date,
        provider_reference=json.get('ID'),
        content=message,
    )
    dao_create_inbound_sms(inbound)
    return inbound


@receive_notifications_blueprint.route('/notifications/sms/receive/firetext', methods=['POST'])
def receive_firetext_sms():
    post_data = request.form

    potential_services = dao_fetch_services_by_sms_sender(post_data['destination'])
    if len(potential_services) != 1:
        current_app.logger.error('Inbound number "{}" not associated with exactly one service'.format(
            post_data['source']
        ))
        statsd_client.incr('inbound.firetext.failed')
        return jsonify({
            "status": "ok"
        }), 200

    service = potential_services[0]

    user_number = normalise_phone_number(post_data['source'])
    message = post_data['message']
    timestamp = post_data['time']

    dao_create_inbound_sms(
        InboundSms(
            service=service,
            notify_number=service.sms_sender,
            user_number=user_number,
            provider_date=timestamp,
            content=message
        )
    )

    statsd_client.incr('inbound.firetext.successful')

    return jsonify({
        "status": "ok"
    }), 200
