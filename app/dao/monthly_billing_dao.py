from datetime import datetime

from app import db
from app.dao.date_util import get_month_start_end_date
from app.dao.notification_usage_dao import get_billing_data_for_month
from app.models import MonthlyBilling, SMS_TYPE, NotificationHistory


def get_service_ids_that_need_sms_billing_populated(start_date, end_date):
    return db.session.query(
        NotificationHistory.service_id
    ).filter(
        NotificationHistory.created_at >= start_date,
        NotificationHistory.created_at <= end_date,
        NotificationHistory.notification_type == SMS_TYPE,
        NotificationHistory.billable_units != 0
    ).distinct().all()


def create_or_update_monthly_billing_sms(service_id, billing_month):
    start_date, end_date = get_month_start_end_date(billing_month)
    monthly = get_billing_data_for_month(service_id=service_id, start_date=start_date, end_date=end_date)
    # update monthly
    monthly_totals = _monthly_billing_data_to_json(monthly)
    row = MonthlyBilling.query.filter_by(year=billing_month.year,
                                         month=datetime.strftime(billing_month, "%B"),
                                         notification_type='sms').first()
    if row:
        row.monthly_totals = monthly_totals
    else:
        row = MonthlyBilling(service_id=service_id,
                             notification_type=SMS_TYPE,
                             year=billing_month.year,
                             month=datetime.strftime(billing_month, "%B"),
                             monthly_totals=monthly_totals)
    db.session.add(row)
    db.session.commit()


def get_monthly_billing_sms(service_id, billing_month):
    monthly = MonthlyBilling.query.filter_by(service_id=service_id,
                                             year=billing_month.year,
                                             month=datetime.strftime(billing_month, "%B"),
                                             notification_type=SMS_TYPE).first()
    return monthly


def _monthly_billing_data_to_json(monthly):
    # total cost must take into account the free allowance.
    # might be a good idea to capture free allowance in this table
    return [{"billing_units": x.billing_units,
             "rate_multiplier": x.rate_multiplier,
             "international": x.international,
             "rate": x.rate,
             "total_cost": (x.billing_units * x.rate_multiplier) * x.rate} for x in monthly]
