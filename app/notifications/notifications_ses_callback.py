from datetime import datetime

from flask import (
    current_app,
    json
)

from app import statsd_client
from app.clients.email.aws_ses import get_aws_responses
from app.dao import (
    notifications_dao
)
from app.dao.service_callback_api_dao import get_service_callback_api_for_service
from app.notifications.process_client_response import validate_callback_data
from app.celery.service_callback_tasks import (
    send_delivery_status_to_service,
    create_encrypted_callback_data,
)
from app.config import QueueNames


def process_ses_response(ses_request):
    client_name = 'SES'
    try:
        errors = validate_callback_data(data=ses_request, fields=['Message'], client_name=client_name)
        if errors:
            return errors

        ses_message = json.loads(ses_request['Message'])
        errors = validate_callback_data(data=ses_message, fields=['notificationType'], client_name=client_name)
        if errors:
            return errors

        notification_type = ses_message['notificationType']
        if notification_type == 'Bounce':
            notification_type = determine_notification_bounce_type(notification_type, ses_message)
        elif notification_type == 'Complaint':
            remove_emails_from_complaint(ses_message)
            current_app.logger.info("Complaint from SES: \n{}".format(ses_message))
            return

        try:
            aws_response_dict = get_aws_responses(notification_type)
        except KeyError:
            error = "{} callback failed: status {} not found".format(client_name, notification_type)
            return error

        notification_status = aws_response_dict['notification_status']

        try:
            reference = ses_message['mail']['messageId']
            notification = notifications_dao.update_notification_status_by_reference(
                reference,
                notification_status
            )
            if not notification:
                warning = "SES callback failed: notification either not found or already updated " \
                          "from sending. Status {} for notification reference {}".format(notification_status, reference)
                current_app.logger.warning(warning)
                return

            if not aws_response_dict['success']:
                current_app.logger.info(
                    "SES delivery failed: notification id {} and reference {} has error found. Status {}".format(
                        notification.id,
                        reference,
                        aws_response_dict['message']
                    )
                )
            else:
                current_app.logger.info('{} callback return status of {} for notification: {}'.format(
                    client_name,
                    notification_status,
                    notification.id))
            statsd_client.incr('callback.ses.{}'.format(notification_status))
            if notification.sent_at:
                statsd_client.timing_with_dates(
                    'callback.ses.elapsed-time'.format(client_name.lower()),
                    datetime.utcnow(),
                    notification.sent_at
                )

            _check_and_queue_callback_task(notification)
            return

        except KeyError:
            error = "SES callback failed: messageId missing"
            return error

    except ValueError:
        error = "{} callback failed: invalid json".format(client_name)
        return error


def determine_notification_bounce_type(notification_type, ses_message):
    current_app.logger.info('SES bounce dict: {}'.format(remove_emails_from_bounce(ses_message['bounce'])))
    if ses_message['bounce']['bounceType'] == 'Permanent':
        notification_type = ses_message['bounce']['bounceType']  # permanent or not
    else:
        notification_type = 'Temporary'
    return notification_type


def remove_emails_from_bounce(bounce_dict):
    for recip in bounce_dict['bouncedRecipients']:
        recip.pop('emailAddress')


def remove_emails_from_complaint(complaint_dict):
    complaint_dict['complaint'].pop('complainedRecipients')


def _check_and_queue_callback_task(notification):
    # queue callback task only if the service_callback_api exists
    service_callback_api = get_service_callback_api_for_service(service_id=notification.service_id)
    if service_callback_api:
        encrypted_notification = create_encrypted_callback_data(notification, service_callback_api)
        send_delivery_status_to_service.apply_async([str(notification.id), encrypted_notification],
                                                    queue=QueueNames.CALLBACKS)
