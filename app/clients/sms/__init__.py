from time import monotonic

from app.clients import Client, ClientException


class SmsClientResponseException(ClientException):
    '''
    Base Exception for SmsClientsResponses
    '''

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"SMS client error ({self.message})"


class SmsClient(Client):
    '''
    Base Sms client for sending smss.
    '''

    def init_app(self, current_app, statsd_client):
        self.current_app = current_app
        self.statsd_client = statsd_client
        self.from_number = self.current_app.config.get('FROM_NUMBER')

    def record_outcome(self, success):
        log_message = "Provider request for {} {}".format(
            self.name,
            "succeeded" if success else "failed",
        )

        if success:
            self.current_app.logger.info(log_message)
            self.statsd_client.incr(f"clients.{self.name}.success")
        else:
            self.statsd_client.incr(f"clients.{self.name}.error")
            self.current_app.logger.warning(log_message)

    def send_sms(self, to, content, reference, international, sender):
        start_time = monotonic()

        if sender is None:
            # temporary log to see if the following ternary is necessary
            # or if it's safe to remove it - keep for 1-2 weeks
            self.current_app.logger.warning(
                f"send_sms called with 'sender' of 'None' for {reference}"
            )

        sender = self.from_number if sender is None else sender

        try:
            response = self.try_send_sms(to, content, reference, international, sender)
            self.record_outcome(True)
        except SmsClientResponseException as e:
            self.record_outcome(False)
            raise e
        finally:
            elapsed_time = monotonic() - start_time
            self.statsd_client.timing(f"clients.{self.name}.request-time", elapsed_time)
            self.current_app.logger.info("Reach request for {} finished in {}".format(reference, elapsed_time))

        return response

    def try_send_sms(self, *args, **kwargs):
        raise NotImplementedError('TODO Need to implement.')

    @property
    def name(self):
        raise NotImplementedError('TODO Need to implement.')
