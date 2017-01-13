from app.models import User
from app.dao.users_dao import save_model_user


def create_user(mobile_number="+447700900986", email="notify@digital.cabinet-office.gov.uk"):
    data = {
        'name': 'Test User',
        'email_address': email,
        'password': 'password',
        'mobile_number': mobile_number,
        'state': 'active'
    }
    user = User.query.filter_by(email_address=email).first()
    if not user:
        user = User(**data)
    save_model_user(user)
    return user
