"""
Messaging service module for the CRM sales app.

Architecture
------------
An Adapter / Strategy pattern decouples the application from any specific
messaging provider. The application always talks to BaseMessagingAdapter;
the concrete implementation is chosen at runtime via get_messaging_adapter().

Adapters
--------
StubAdapter   — Development/test adapter. Logs to stdout; never calls external APIs.
TwilioAdapter — Production adapter using Twilio REST API for SMS and WhatsApp.

Usage
-----
    from sales.services.messaging import get_messaging_adapter

    adapter = get_messaging_adapter()
    adapter.send_sms(to='+919876543210', body='Hello!')
    adapter.send_whatsapp(to='+919876543210', body='Hello!')

Configuration (settings.py / .env)
-----------------------------------
    MESSAGING_ADAPTER = 'stub'   # or 'twilio'
    TWILIO_ACCOUNT_SID = '...'
    TWILIO_AUTH_TOKEN  = '...'
    TWILIO_FROM_NUMBER = '+1...'
    TWILIO_WHATSAPP_FROM = 'whatsapp:+14155238886'
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base adapter interface
# ---------------------------------------------------------------------------

class BaseMessagingAdapter:
    """Abstract interface that all messaging adapters must implement."""

    def send_sms(self, to: str, body: str) -> dict:
        """Send an SMS message. Returns a dict with delivery info."""
        raise NotImplementedError(
            f'{self.__class__.__name__} must implement send_sms()'
        )

    def send_whatsapp(self, to: str, body: str) -> dict:
        """Send a WhatsApp message. Returns a dict with delivery info."""
        raise NotImplementedError(
            f'{self.__class__.__name__} must implement send_whatsapp()'
        )


# ---------------------------------------------------------------------------
# Stub adapter (development / testing)
# ---------------------------------------------------------------------------

class StubAdapter(BaseMessagingAdapter):
    """
    No-op adapter for local development and automated tests.

    All calls are logged at INFO level but never reach any external API.
    This means the application is fully functional without Twilio credentials.
    """

    def send_sms(self, to: str, body: str) -> dict:
        logger.info('[STUB SMS] To: %s | Body: %s', to, body)
        return {'adapter': 'stub', 'channel': 'sms', 'to': to, 'status': 'stub_sent'}

    def send_whatsapp(self, to: str, body: str) -> dict:
        logger.info('[STUB WhatsApp] To: %s | Body: %s', to, body)
        return {'adapter': 'stub', 'channel': 'whatsapp', 'to': to, 'status': 'stub_sent'}


# ---------------------------------------------------------------------------
# Twilio adapter (production)
# ---------------------------------------------------------------------------

class TwilioAdapter(BaseMessagingAdapter):
    """
    Production adapter that uses the Twilio Programmable Messaging API.

    SMS  → standard Twilio number
    WhatsApp → Twilio WhatsApp Sandbox (or approved Business profile)
    """

    def __init__(self):
        try:
            from twilio.rest import Client  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                'The "twilio" package is required to use TwilioAdapter. '
                'Run: pip install twilio'
            ) from exc

        self._client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
        )
        self._from_number: str = settings.TWILIO_FROM_NUMBER
        self._whatsapp_from: str = settings.TWILIO_WHATSAPP_FROM

    def send_sms(self, to: str, body: str) -> dict:
        message = self._client.messages.create(
            to=to,
            from_=self._from_number,
            body=body,
        )
        logger.info('SMS sent: sid=%s status=%s to=%s', message.sid, message.status, to)
        return {'sid': message.sid, 'status': message.status, 'to': to}

    def send_whatsapp(self, to: str, body: str) -> dict:
        # Twilio requires the "whatsapp:" prefix on the recipient number
        whatsapp_to = to if to.startswith('whatsapp:') else f'whatsapp:{to}'
        message = self._client.messages.create(
            to=whatsapp_to,
            from_=self._whatsapp_from,
            body=body,
        )
        logger.info(
            'WhatsApp sent: sid=%s status=%s to=%s',
            message.sid,
            message.status,
            whatsapp_to,
        )
        return {'sid': message.sid, 'status': message.status, 'to': whatsapp_to}


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

_ADAPTERS: dict[str, type[BaseMessagingAdapter]] = {
    'stub': StubAdapter,
    'twilio': TwilioAdapter,
}


def get_messaging_adapter() -> BaseMessagingAdapter:
    """
    Return the configured messaging adapter instance.

    Reads MESSAGING_ADAPTER from Django settings (default: 'stub').
    Raises ValueError for unknown adapter names so misconfiguration is caught early.
    """
    name = getattr(settings, 'MESSAGING_ADAPTER', 'stub').lower().strip()
    adapter_class = _ADAPTERS.get(name)
    if adapter_class is None:
        raise ValueError(
            f'Unknown MESSAGING_ADAPTER: {name!r}. '
            f'Valid options: {list(_ADAPTERS)}'
        )
    return adapter_class()
