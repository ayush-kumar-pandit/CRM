# sales/services/messaging.py — re-exported from __init__.py
from . import get_messaging_adapter, StubAdapter, TwilioAdapter, BaseMessagingAdapter

__all__ = ['get_messaging_adapter', 'StubAdapter', 'TwilioAdapter', 'BaseMessagingAdapter']
