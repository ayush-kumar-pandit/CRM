from django import template
from django.utils.html import format_html
register = template.Library()

@register.filter(is_safe=True)
def status_badge(status):
    config = {
        'pending': ('bg-amber-100 text-amber-800 ring-amber-600/20', 'Pending'),
        'completed': ('bg-emerald-100 text-emerald-800 ring-emerald-600/20', 'Completed'),
        'followed_up': ('bg-indigo-100 text-indigo-800 ring-indigo-600/20', 'Followed-Up'),
    }
    css, label = config.get(status, ('bg-slate-100 text-slate-700 ring-slate-600/20', status.title()))
    return format_html('<span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset {}">{}</span>', css, label)

@register.filter(is_safe=True)
def message_status_badge(status):
    config = {
        'queued': ('bg-slate-100 text-slate-700 ring-slate-600/20', 'Queued'),
        'sent': ('bg-emerald-100 text-emerald-800 ring-emerald-600/20', 'Sent'),
        'failed': ('bg-red-100 text-red-800 ring-red-600/20', 'Failed'),
    }
    css, label = config.get(status, ('bg-slate-100 text-slate-700 ring-slate-600/20', status.title()))
    return format_html('<span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset {}">{}</span>', css, label)

@register.filter
def channel_icon(channel):
    return {'sms': '💬', 'whatsapp': '📱'}.get(channel, '📨')

@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    updated = context['request'].GET.copy()
    for key, value in kwargs.items():
        if value is not None:
            updated[key] = value
        elif key in updated:
            del updated[key]
    return updated.urlencode()

@register.filter
def currency(value):
    try:
        return f'₹{float(value):,.2f}'
    except (TypeError, ValueError):
        return str(value)

@register.filter
def truncate_chars(value, max_length):
    value = str(value)
    return value if len(value) <= max_length else value[:max_length].rstrip() + '…'
