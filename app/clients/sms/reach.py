import json

from requests import RequestException, request

from app.clients.sms import SmsClient, SmsClientResponseException


def get_reach_responses(status, detailed_status_code=None):
    if status == 'TODO-d':
        return ("delivered", "TODO: Delivered")
    elif status == 'TODO-tf':
        return ("temporary-failure", "TODO: Temporary failure")
    elif status == 'TODO-pf':
        return ("permanent-failure", "TODO: Permanent failure")
    else:
        raise KeyError


class ReachClient(SmsClient):
    def init_app(self, *args, **kwargs):
        super().init_app(*args, **kwargs)
        self.url = self.current_app.config.get('REACH_URL')

    @property
    def name(self):
        return 'reach'

    def try_send_sms(self, to, content, reference, international, sender):
        data = {
            # TODO
        }

        try:
            response = request(
                "POST",
                self.url,
                data=json.dumps(data),
                headers={
                    'Content-Type': 'application/json',
                },
                timeout=60
            )

            response.raise_for_status()
            try:
                json.loads(response.text)
            except (ValueError, AttributeError):
                raise SmsClientResponseException("Invalid response JSON")
        except RequestException:
            raise SmsClientResponseException("Request failed")

        return response
