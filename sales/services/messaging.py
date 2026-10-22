"""
Messaging adapters reused by both sales and orders apps.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class BaseMessagingAdapter:
    def send_sms(self, to: str, body: str) -> dict:
        raise NotImplementedError

    def send_whatsapp(self, to: str, body: str) -> dict:
        raise NotImplementedError


class StubAdapter(BaseMessagingAdapter):
    """Dev/test adapter — logs only, no external calls."""
    def send_sms(self, to, body):
        logger.info('[STUB SMS] To: %s | Body: %s', to, body)
        return {'status': 'stub_sent', 'to': to}

    def send_whatsapp(self, to, body):
        logger.info('[STUB WhatsApp] To: %s | Body: %s', to, body)
        return {'status': 'stub_sent', 'to': to}


class TwilioAdapter(BaseMessagingAdapter):
    """Production adapter using Twilio Programmable Messaging."""
    def __init__(self):
        from twilio.rest import Client
        self._client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self._from_number = settings.TWILIO_FROM_NUMBER
        self._whatsapp_from = settings.TWILIO_WHATSAPP_FROM

    def send_sms(self, to, body):
        msg = self._client.messages.create(to=to, from_=self._from_number, body=body)
        logger.info('SMS sent: sid=%s to=%s', msg.sid, to)
        return {'sid': msg.sid, 'status': msg.status}

    def send_whatsapp(self, to, body):
        wa_to = to if to.startswith('whatsapp:') else f'whatsapp:{to}'
        msg = self._client.messages.create(to=wa_to, from_=self._whatsapp_from, body=body)
        logger.info('WhatsApp sent: sid=%s to=%s', msg.sid, wa_to)
        return {'sid': msg.sid, 'status': msg.status}


def get_messaging_adapter() -> BaseMessagingAdapter:
    """Return StubAdapter (dev) or TwilioAdapter (production)."""
    name = getattr(settings, 'MESSAGING_ADAPTER', 'stub').lower().strip()
    return TwilioAdapter() if name == 'twilio' else StubAdapter()
