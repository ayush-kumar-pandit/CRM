# sales/services/__init__.py
from .messaging import get_messaging_adapter, StubAdapter, TwilioAdapter, BaseMessagingAdapter

__all__ = ['get_messaging_adapter', 'StubAdapter', 'TwilioAdapter', 'BaseMessagingAdapter']
