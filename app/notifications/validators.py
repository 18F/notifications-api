from flask import current_app

from app.dao import services_dao
from app.models import KEY_TYPE_TEST, KEY_TYPE_TEAM
from app.service.utils import service_allowed_to_send_to
from app.v2.errors import TooManyRequestsError, BadRequestError


def check_service_message_limit(key_type, service):
    if all((key_type != KEY_TYPE_TEST,
            service.restricted)):
        service_stats = services_dao.fetch_todays_total_message_count(service.id)
        if service_stats >= service.message_limit:
            raise TooManyRequestsError(service.message_limit)


def check_template_is_for_notification_type(notification_type, template_type):
    if notification_type != template_type:
        raise BadRequestError(
            message="{0} template is not suitable for {1} notification".format(template_type,
                                                                               notification_type),
            fields=[{"template": "{0} template is not suitable for {1} notification".format(template_type,
                                                                                            notification_type)}])


def check_template_is_active(template):
    if template.archived:
        raise BadRequestError(fields=[{"template": "has been deleted"}],
                              message="Template has been deleted")


def service_can_send_to_recipient(send_to, key_type, service, recipient_type):
    if not service_allowed_to_send_to(send_to, service, key_type):
        if key_type == KEY_TYPE_TEAM:
            message = 'Can’t send to this recipient using a team-only API key'
        else:
            message = (
                'Can’t send to this recipient when service is in trial mode '
                '– see https://www.notifications.service.gov.uk/trial-mode'
            )
        raise BadRequestError(
            fields={recipient_type: [message]}
        )


def check_sms_content_char_count(content_count):
    char_count_limit = current_app.config.get('SMS_CHAR_COUNT_LIMIT')
    if (
        content_count > char_count_limit
    ):
        message = 'Content has a character count greater than the limit of {}'.format(char_count_limit)
        errors = {'content': [message]}
        raise BadRequestError(fields=errors)
