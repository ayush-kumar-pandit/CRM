"""
Custom template tags and filters for the CRM sales app.

Usage in templates: {% load crm_extras %}

Tags / Filters
--------------
status_badge(status)         — Renders a pill badge for Sale.status
message_status_badge(status) — Renders a pill badge for MessageLog.status
channel_icon(channel)        — Returns an emoji icon for sms/whatsapp
query_transform(request, **kwargs) — Modifies current GET params for pagination links
currency(value)              — Formats a Decimal as a currency string
"""

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


# ---------------------------------------------------------------------------
# status_badge
# ---------------------------------------------------------------------------

@register.filter(is_safe=True)
def status_badge(status: str) -> str:
    """Render a colour-coded pill badge for a Sale status value."""
    config = {
        'pending':     ('bg-amber-100 text-amber-800 ring-amber-600/20',   'Pending'),
        'completed':   ('bg-emerald-100 text-emerald-800 ring-emerald-600/20', 'Completed'),
        'followed_up': ('bg-indigo-100 text-indigo-800 ring-indigo-600/20', 'Followed-Up'),
    }
    css, label = config.get(status, ('bg-slate-100 text-slate-700 ring-slate-600/20', status.title()))
    return format_html(
        '<span class="inline-flex items-center rounded-full px-2.5 py-0.5 '
        'text-xs font-medium ring-1 ring-inset {}">{}</span>',
        css,
        label,
    )


# ---------------------------------------------------------------------------
# message_status_badge
# ---------------------------------------------------------------------------

@register.filter(is_safe=True)
def message_status_badge(status: str) -> str:
    """Render a colour-coded pill badge for a MessageLog status value."""
    config = {
        'queued': ('bg-slate-100 text-slate-700 ring-slate-600/20', 'Queued'),
        'sent':   ('bg-emerald-100 text-emerald-800 ring-emerald-600/20', 'Sent'),
        'failed': ('bg-red-100 text-red-800 ring-red-600/20', 'Failed'),
    }
    css, label = config.get(status, ('bg-slate-100 text-slate-700 ring-slate-600/20', status.title()))
    return format_html(
        '<span class="inline-flex items-center rounded-full px-2.5 py-0.5 '
        'text-xs font-medium ring-1 ring-inset {}">{}</span>',
        css,
        label,
    )


# ---------------------------------------------------------------------------
# channel_icon
# ---------------------------------------------------------------------------

@register.filter
def channel_icon(channel: str) -> str:
    """Return a text emoji representing the messaging channel."""
    icons = {
        'sms':       '💬',
        'whatsapp':  '📱',
    }
    return icons.get(channel, '📨')


# ---------------------------------------------------------------------------
# query_transform
# ---------------------------------------------------------------------------

@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """
    Render the current GET query string with specified keys overridden.

    Usage in template:
        <a href="?{% query_transform page=page_obj.next_page_number %}">Next</a>
    """
    request = context['request']
    updated = request.GET.copy()
    for key, value in kwargs.items():
        if value is not None:
            updated[key] = value
        elif key in updated:
            del updated[key]
    return updated.urlencode()


# ---------------------------------------------------------------------------
# currency
# ---------------------------------------------------------------------------

@register.filter
def currency(value) -> str:
    """Format a numeric value as a currency string (₹)."""
    try:
        return f'₹{float(value):,.2f}'
    except (TypeError, ValueError):
        return str(value)


# ---------------------------------------------------------------------------
# truncate_chars (convenience alias)
# ---------------------------------------------------------------------------

@register.filter
def truncate_chars(value: str, max_length: int) -> str:
    """Truncate a string to max_length characters, appending '…' if needed."""
    value = str(value)
    if len(value) <= max_length:
        return value
    return value[:max_length].rstrip() + '…'
