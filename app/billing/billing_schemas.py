from datetime import datetime

create_or_update_free_sms_fragment_limit_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "description": "POST annual billing schema",
    "type": "object",
    "title": "Create",
    "properties": {
        "free_sms_fragment_limit": {"type": "integer", "minimum": 0},
    },
    "required": ["free_sms_fragment_limit"]
}


def serialize_ft_billing_remove_emails(rows):
    return [
        {
            "month": (datetime.strftime(row.month, "%B")),
            "notification_type": row.notification_type,
            # TEMPORARY: while we migrate to "chargeable_units" in the Admin app
            "billing_units": row.billable_units,
            "chargeable_units": row.chargeable_units,
            "rate": float(row.rate),
            "postage": row.postage,
        }
        for row in rows
        if row.notification_type != 'email'
    ]


def serialize_ft_billing_yearly_totals(rows):
    return [
        {
            "notification_type": row.notification_type,
            # TEMPORARY: while we migrate to "chargeable_units" in the Admin app
            "billing_units": row.billable_units,
            "chargeable_units": row.chargeable_units,
            "rate": float(row.rate),
            # TEMPORARY: while we migrate to "cost" in the Admin app
            "letter_total": float(row.billable_units * row.rate) if row.notification_type == 'letter' else 0,
            "cost": float(row.cost),
        }
        for row in rows
    ]
