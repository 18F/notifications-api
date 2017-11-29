from flask import (
    Blueprint,
    jsonify,
    request,
)
from sqlalchemy.exc import SQLAlchemyError

from app.dao.service_inbound_api_dao import (
    save_service_inbound_api,
    reset_service_inbound_api,
    get_service_inbound_api
)
from app.errors import (
    register_errors
)
from app.models import (
    ServiceInboundApi,
)
from app.schema_validation import validate
from app.service.service_callback_api_schema import (
    create_service_callback_api_schema,
    update_service_callback_api_schema
)

service_callback_blueprint = Blueprint('service_callback', __name__, url_prefix='/service/<uuid:service_id>')

register_errors(service_callback_blueprint)


@service_callback_blueprint.route('/inbound-api', methods=['POST'])
def create_service_inbound_api(service_id):
    data = request.get_json()
    validate(data, create_service_callback_api_schema)
    data["service_id"] = service_id
    inbound_api = ServiceInboundApi(**data)
    try:
        save_service_inbound_api(inbound_api)
    except SQLAlchemyError as e:
        return handle_sql_error(e)

    return jsonify(data=inbound_api.serialize()), 201


@service_callback_blueprint.route('/inbound-api/<uuid:inbound_api_id>', methods=['POST'])
def update_service_inbound_api(service_id, inbound_api_id):
    data = request.get_json()
    validate(data, update_service_callback_api_schema)

    to_update = get_service_inbound_api(inbound_api_id, service_id)

    reset_service_inbound_api(service_inbound_api=to_update,
                              updated_by_id=data["updated_by_id"],
                              url=data.get("url", None),
                              bearer_token=data.get("bearer_token", None))
    return jsonify(data=to_update.serialize()), 200


@service_callback_blueprint.route('/inbound-api/<uuid:inbound_api_id>', methods=["GET"])
def fetch_service_inbound_api(service_id, inbound_api_id):
    inbound_api = get_service_inbound_api(inbound_api_id, service_id)

    return jsonify(data=inbound_api.serialize()), 200


def handle_sql_error(e):
    if hasattr(e, 'orig') and hasattr(e.orig, 'pgerror') and e.orig.pgerror \
            and ('duplicate key value violates unique constraint "ix_service_inbound_api_service_id"'
                 in e.orig.pgerror):
        return jsonify(
            result='error',
            message={'name': ["You can only have one URL and bearer token for your service."]}
        ), 400
    elif hasattr(e, 'orig') and hasattr(e.orig, 'pgerror') and e.orig.pgerror \
            and ('insert or update on table "service_inbound_api" violates '
                 'foreign key constraint "service_inbound_api_service_id_fkey"'
                 in e.orig.pgerror):
        return jsonify(result='error', message="No result found"), 404
    else:
        raise e
