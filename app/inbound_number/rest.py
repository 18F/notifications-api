from flask import Blueprint, jsonify, request

from app.dao.inbound_numbers_dao import (
    dao_get_inbound_numbers,
    dao_get_inbound_number_for_service,
    dao_get_available_inbound_numbers,
    dao_set_inbound_number_to_service,
    dao_set_inbound_number_active_flag_for_service
)
from app.errors import register_errors
from app.models import InboundNumber
from app.schema_validation import validate

inbound_number_blueprint = Blueprint('inbound_number', __name__)
register_errors(inbound_number_blueprint)


@inbound_number_blueprint.route('', methods=['GET'])
def get_inbound_numbers():
    inbound_numbers = [i.serialize() for i in dao_get_inbound_numbers()]

    return jsonify(data=inbound_numbers)


@inbound_number_blueprint.route('/<uuid:service_id>', methods=['POST'])
def post_allocate_or_reactivate_inbound_number(service_id):
    inbound_number = dao_get_inbound_number_for_service(service_id)

    if not inbound_number:
        available_numbers = dao_get_available_inbound_numbers()

        if len(available_numbers) > 0:
            dao_set_inbound_number_to_service(service_id, available_numbers[0])
            return '', 204
        else:
            return '', 409
    else:
        dao_set_inbound_number_active_flag_for_service(service_id, active=True)
        return '', 204


@inbound_number_blueprint.route('/<uuid:service_id>/off', methods=['POST'])
def post_deactivate_inbound_number(service_id):
    dao_set_inbound_number_active_flag_for_service(service_id, active=False)
    return '', 204
