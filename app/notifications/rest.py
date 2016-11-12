from datetime import datetime

from flask import (
    Blueprint,
    jsonify,
    request,
    current_app,
    json
)
from notifications_utils.renderers import PassThrough
from notifications_utils.template import Template

from app import api_user, create_uuid, statsd_client
from app.clients.email.aws_ses import get_aws_responses
from app.dao import (
    templates_dao,
    services_dao,
    notifications_dao
)
from app.models import KEY_TYPE_TEAM
from app.models import SMS_TYPE
from app.notifications.process_client_response import (
    validate_callback_data,
    process_sms_client_response
)
from app.notifications.process_notifications import persist_notification, send_notification_to_queue
from app.notifications.validators import check_service_message_limit, check_template_is_for_notification_type, \
    check_template_is_active
from app.schemas import (
    email_notification_schema,
    sms_template_notification_schema,
    notification_with_personalisation_schema,
    notifications_filter_schema,
    notifications_statistics_schema,
    day_schema
)
from app.service.utils import service_allowed_to_send_to
from app.utils import pagination_links
from app import redis_store
from app.clients import redis

notifications = Blueprint('notifications', __name__)

from app.errors import (
    register_errors,
    InvalidRequest
)


register_errors(notifications)


@notifications.route('/notifications/email/ses', methods=['POST'])
def process_ses_response():
    client_name = 'SES'
    try:
        ses_request = json.loads(request.data)
        errors = validate_callback_data(data=ses_request, fields=['Message'], client_name=client_name)
        if errors:
            raise InvalidRequest(errors, status_code=400)

        ses_message = json.loads(ses_request['Message'])
        errors = validate_callback_data(data=ses_message, fields=['notificationType'], client_name=client_name)
        if errors:
            raise InvalidRequest(errors, status_code=400)

        notification_type = ses_message['notificationType']
        if notification_type == 'Bounce':
            if ses_message['bounce']['bounceType'] == 'Permanent':
                notification_type = ses_message['bounce']['bounceType']  # permanent or not
            else:
                notification_type = 'Temporary'
        try:
            aws_response_dict = get_aws_responses(notification_type)
        except KeyError:
            error = "{} callback failed: status {} not found".format(client_name, notification_type)
            raise InvalidRequest(error, status_code=400)

        notification_status = aws_response_dict['notification_status']

        try:
            reference = ses_message['mail']['messageId']
            notification = notifications_dao.update_notification_status_by_reference(
                reference,
                notification_status
            )
            if not notification:
                error = "SES callback failed: notification either not found or already updated " \
                        "from sending. Status {}".format(notification_status)
                raise InvalidRequest(error, status_code=404)

            if not aws_response_dict['success']:
                current_app.logger.info(
                    "SES delivery failed: notification {} has error found. Status {}".format(
                        reference,
                        aws_response_dict['message']
                    )
                )

            statsd_client.incr('callback.ses.{}'.format(notification_status))
            if notification.sent_at:
                statsd_client.timing_with_dates(
                    'callback.ses.elapsed-time'.format(client_name.lower()),
                    datetime.utcnow(),
                    notification.sent_at
                )
            return jsonify(
                result="success", message="SES callback succeeded"
            ), 200

        except KeyError:
            message = "SES callback failed: messageId missing"
            raise InvalidRequest(message, status_code=400)

    except ValueError as ex:
        error = "{} callback failed: invalid json".format(client_name)
        raise InvalidRequest(error, status_code=400)


@notifications.route('/notifications/sms/mmg', methods=['POST'])
def process_mmg_response():
    client_name = 'MMG'
    data = json.loads(request.data)
    errors = validate_callback_data(data=data,
                                    fields=['status', 'CID'],
                                    client_name=client_name)
    if errors:
        raise InvalidRequest(errors, status_code=400)

    success, errors = process_sms_client_response(status=str(data.get('status')),
                                                  reference=data.get('CID'),
                                                  client_name=client_name)
    if errors:
        raise InvalidRequest(errors, status_code=400)
    else:
        return jsonify(result='success', message=success), 200


@notifications.route('/notifications/sms/firetext', methods=['POST'])
def process_firetext_response():
    client_name = 'Firetext'
    errors = validate_callback_data(data=request.form,
                                    fields=['status', 'reference'],
                                    client_name=client_name)
    if errors:
        raise InvalidRequest(errors, status_code=400)

    response_code = request.form.get('code')
    status = request.form.get('status')
    current_app.logger.info('Firetext status: {}, extended error code: {}'.format(status, response_code))

    success, errors = process_sms_client_response(status=status,
                                                  reference=request.form.get('reference'),
                                                  client_name=client_name)
    if errors:
        raise InvalidRequest(errors, status_code=400)
    else:
        return jsonify(result='success', message=success), 200


@notifications.route('/notifications/<uuid:notification_id>', methods=['GET'])
def get_notification_by_id(notification_id):
    notification = notifications_dao.get_notification_with_personalisation(str(api_user.service_id),
                                                                           notification_id,
                                                                           key_type=None)
    return jsonify(data={"notification": notification_with_personalisation_schema.dump(notification).data}), 200


@notifications.route('/notifications', methods=['GET'])
def get_all_notifications():
    data = notifications_filter_schema.load(request.args).data
    include_jobs = data.get('include_jobs', False)
    page = data['page'] if 'page' in data else 1
    page_size = data['page_size'] if 'page_size' in data else current_app.config.get('PAGE_SIZE')
    limit_days = data.get('limit_days')

    pagination = notifications_dao.get_notifications_for_service(
        str(api_user.service_id),
        personalisation=True,
        filter_dict=data,
        page=page,
        page_size=page_size,
        limit_days=limit_days,
        key_type=api_user.key_type,
        include_jobs=include_jobs)
    return jsonify(
        notifications=notification_with_personalisation_schema.dump(pagination.items, many=True).data,
        page_size=page_size,
        total=pagination.total,
        links=pagination_links(
            pagination,
            '.get_all_notifications',
            **request.args.to_dict()
        )
    ), 200


@notifications.route('/notifications/statistics')
def get_notification_statistics_for_day():
    data = day_schema.load(request.args).data
    statistics = notifications_dao.dao_get_potential_notification_statistics_for_day(
        day=data['day']
    )
    data, errors = notifications_statistics_schema.dump(statistics, many=True)
    return jsonify(data=data), 200


@notifications.route('/notifications/<string:notification_type>', methods=['POST'])
def send_notification(notification_type):

    if notification_type not in ['sms', 'email']:
        assert False

    service_id = str(api_user.service_id)
    service = services_dao.dao_fetch_service_by_id(service_id)

    notification, errors = (
        sms_template_notification_schema if notification_type == SMS_TYPE else email_notification_schema
    ).load(request.get_json())
    if errors:
        raise InvalidRequest(errors, status_code=400)

    check_service_message_limit(api_user.key_type, service)

    template = templates_dao.dao_get_template_by_id_and_service_id(template_id=notification['template'],
                                                                   service_id=service_id)

    check_template_is_for_notification_type(notification_type, template.template_type)
    check_template_is_active(template)

    template_object = create_template_object_for_notification(template, notification.get('personalisation', {}))

    _service_allowed_to_send_to(notification, service)

    saved_notification = None
    if not _simulated_recipient(notification['to'], notification_type):
        saved_notification = persist_notification(template_id=template.id,
                                                  template_version=template.version,
                                                  recipient=notification['to'],
                                                  service_id=service.id,
                                                  personalisation=notification.get('personalisation', None),
                                                  notification_type=notification_type,
                                                  api_key_id=api_user.id,
                                                  key_type=api_user.key_type)
        send_notification_to_queue(saved_notification, service.research_mode)

    notification_id = create_uuid() if saved_notification is None else saved_notification.id
    notification.update({"template_version": template.version})
    redis_store.incr(redis.cache_key(service.id))
    return jsonify(
        data=get_notification_return_data(
            notification_id,
            notification,
            template_object)
    ), 201


def get_notification_return_data(notification_id, notification, template):
    output = {
        'body': template.replaced,
        'template_version': notification['template_version'],
        'notification': {'id': notification_id}
    }

    if template.template_type == 'email':
        output.update({'subject': template.replaced_subject})

    return output


def _simulated_recipient(to_address, notification_type):
    return (to_address in current_app.config['SIMULATED_SMS_NUMBERS']
            if notification_type == SMS_TYPE
            else to_address in current_app.config['SIMULATED_EMAIL_ADDRESSES'])


def _service_allowed_to_send_to(notification, service):
    if not service_allowed_to_send_to(notification['to'], service, api_user.key_type):
        if api_user.key_type == KEY_TYPE_TEAM:
            message = 'Can’t send to this recipient using a team-only API key'
        else:
            message = (
                'Can’t send to this recipient when service is in trial mode '
                '– see https://www.notifications.service.gov.uk/trial-mode'
            )
        raise InvalidRequest(
            {'to': [message]},
            status_code=400
        )


def create_template_object_for_notification(template, personalisation):
    template_object = Template(
        template.__dict__,
        personalisation,
        renderer=PassThrough()
    )
    if template_object.missing_data:
        message = 'Missing personalisation: {}'.format(", ".join(template_object.missing_data))
        errors = {'template': [message]}
        raise InvalidRequest(errors, status_code=400)

    if template_object.additional_data:
        message = 'Personalisation not needed for template: {}'.format(", ".join(template_object.additional_data))
        errors = {'template': [message]}
        raise InvalidRequest(errors, status_code=400)

    if (
        template_object.template_type == SMS_TYPE and
        template_object.replaced_content_count > current_app.config.get('SMS_CHAR_COUNT_LIMIT')
    ):
        char_count = current_app.config.get('SMS_CHAR_COUNT_LIMIT')
        message = 'Content has a character count greater than the limit of {}'.format(char_count)
        errors = {'content': [message]}
        raise InvalidRequest(errors, status_code=400)
    return template_object
