import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class BaseMessagingAdapter:
    def send_sms(self, to, body): raise NotImplementedError
    def send_whatsapp(self, to, body): raise NotImplementedError


class StubAdapter(BaseMessagingAdapter):
    def send_sms(self, to, body):
        logger.info('[STUB SMS] To: %s | Body: %s', to, body)
        return {'status': 'stub_sent', 'to': to}

    def send_whatsapp(self, to, body):
        logger.info('[STUB WhatsApp] To: %s | Body: %s', to, body)
        return {'status': 'stub_sent', 'to': to}


class TwilioAdapter(BaseMessagingAdapter):
    def __init__(self):
        from twilio.rest import Client
        self._client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self._from_number = settings.TWILIO_FROM_NUMBER
        self._whatsapp_from = settings.TWILIO_WHATSAPP_FROM

    def send_sms(self, to, body):
        msg = self._client.messages.create(to=to, from_=self._from_number, body=body)
        return {'sid': msg.sid, 'status': msg.status}

    def send_whatsapp(self, to, body):
        wa_to = to if to.startswith('whatsapp:') else f'whatsapp:{to}'
        msg = self._client.messages.create(to=wa_to, from_=self._whatsapp_from, body=body)
        return {'sid': msg.sid, 'status': msg.status}


def get_messaging_adapter():
    name = getattr(settings, 'MESSAGING_ADAPTER', 'stub').lower()
    return TwilioAdapter() if name == 'twilio' else StubAdapter()
