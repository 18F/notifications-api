from datetime import datetime, timedelta
import pytest
from app.dao.notifications_dao import dao_get_last_template_usage, dao_get_last_date_template_was_used
from tests.app.db import create_notification, create_template, create_ft_notification_status


def test_last_template_usage_should_get_right_data(sample_notification):
    results = dao_get_last_template_usage(sample_notification.template_id, 'sms', sample_notification.service_id)
    assert results.template.name == 'sms Template Name'
    assert results.template.template_type == 'sms'
    assert results.created_at == sample_notification.created_at
    assert results.template_id == sample_notification.template_id
    assert results.id == sample_notification.id


@pytest.mark.parametrize('notification_type', ['sms', 'email', 'letter'])
def test_last_template_usage_should_be_able_to_get_all_template_usage_history_order_by_notification_created_at(
        sample_service,
        notification_type
):
    template = create_template(sample_service, template_type=notification_type)

    create_notification(template, created_at=datetime.utcnow() - timedelta(seconds=1))
    create_notification(template, created_at=datetime.utcnow() - timedelta(seconds=2))
    create_notification(template, created_at=datetime.utcnow() - timedelta(seconds=3))
    most_recent = create_notification(template)

    results = dao_get_last_template_usage(template.id, notification_type, template.service_id)
    assert results.id == most_recent.id


def test_last_template_usage_should_ignore_test_keys(
        sample_template,
        sample_team_api_key,
        sample_test_api_key
):
    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
    two_minutes_ago = datetime.utcnow() - timedelta(minutes=2)

    team_key = create_notification(
        template=sample_template,
        created_at=two_minutes_ago,
        api_key=sample_team_api_key)
    create_notification(
        template=sample_template,
        created_at=one_minute_ago,
        api_key=sample_test_api_key)

    results = dao_get_last_template_usage(sample_template.id, 'sms', sample_template.service_id)
    assert results.id == team_key.id


def test_last_template_usage_should_be_able_to_get_no_template_usage_history_if_no_notifications_using_template(
        sample_template):
    results = dao_get_last_template_usage(sample_template.id, 'sms', sample_template.service_id)
    assert not results


def test_dao_get_last_date_template_was_used_returns_bst_date_from_stats_table(
        sample_template
):
    last_status_date = (datetime.utcnow() - timedelta(days=2)).date()
    create_ft_notification_status(bst_date=last_status_date,
                                  template=sample_template)

    last_used_date = dao_get_last_date_template_was_used(template_id=sample_template.id,
                                                         service_id=sample_template.service_id)
    assert last_used_date == last_status_date


def test_dao_get_last_date_template_was_used_returns_created_at_from_notifications(
        sample_template
):
    last_notification_date = datetime.utcnow() - timedelta(hours=2)
    create_notification(template=sample_template, created_at=last_notification_date)

    last_status_date = (datetime.utcnow() - timedelta(days=2)).date()
    create_ft_notification_status(bst_date=last_status_date, template=sample_template)
    last_used_date = dao_get_last_date_template_was_used(template_id=sample_template.id,
                                                         service_id=sample_template.service_id)
    assert last_used_date == last_notification_date


def test_dao_get_last_date_template_was_used_returns_none_if_never_used(sample_template):
    assert not dao_get_last_date_template_was_used(template_id=sample_template.id,
                                                   service_id=sample_template.service_id)
