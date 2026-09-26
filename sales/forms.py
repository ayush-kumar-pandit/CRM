"""
Django forms for the CRM sales app.

Forms
-----
SaleForm                — Create/Edit Sale with E.164 phone validation
NotificationTemplateForm — Create/Edit notification templates
CRMSettingsForm         — Update global CRM settings
"""

import phonenumbers
from django import forms
from django.core.exceptions import ValidationError

from .models import CRMSettings, NotificationTemplate, Sale

# ---------------------------------------------------------------------------
# Shared widget CSS — Tailwind-styled inputs
# ---------------------------------------------------------------------------

_INPUT_CLASS = (
    'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 '
    'text-sm text-slate-900 shadow-sm placeholder:text-slate-400 '
    'focus:border-indigo-500 focus:outline-none focus:ring-1 '
    'focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-50'
)

_SELECT_CLASS = (
    'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 '
    'text-sm text-slate-900 shadow-sm '
    'focus:border-indigo-500 focus:outline-none focus:ring-1 '
    'focus:ring-indigo-500'
)

_TEXTAREA_CLASS = (
    'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 '
    'text-sm text-slate-900 shadow-sm placeholder:text-slate-400 '
    'focus:border-indigo-500 focus:outline-none focus:ring-1 '
    'focus:ring-indigo-500 resize-y'
)

_CHECKBOX_CLASS = (
    'h-4 w-4 rounded border-slate-300 text-indigo-600 '
    'focus:ring-indigo-500'
)


# ---------------------------------------------------------------------------
# SaleForm
# ---------------------------------------------------------------------------

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = [
            'customer_name', 'email', 'phone_number',
            'product_name', 'quantity', 'price',
            'shipping_address', 'status', 'notes',
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': 'Jane Doe',
            }),
            'email': forms.EmailInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': 'jane@example.com',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': '+919876543210',
            }),
            'product_name': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': 'Product SKU or name',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': _INPUT_CLASS,
                'min': 1,
            }),
            'price': forms.NumberInput(attrs={
                'class': _INPUT_CLASS,
                'step': '0.01',
                'placeholder': '0.00',
            }),
            'shipping_address': forms.Textarea(attrs={
                'class': _TEXTAREA_CLASS,
                'rows': 3,
                'placeholder': 'Full shipping address…',
            }),
            'status': forms.Select(attrs={'class': _SELECT_CLASS}),
            'notes': forms.Textarea(attrs={
                'class': _TEXTAREA_CLASS,
                'rows': 2,
                'placeholder': 'Optional internal notes…',
            }),
        }
        labels = {
            'phone_number': 'Phone Number (E.164)',
        }
        help_texts = {
            'phone_number': 'Include country code, e.g. +919876543210',
            'price': 'Unit price per item.',
        }

    def clean_phone_number(self):
        raw = self.cleaned_data.get('phone_number', '').strip()
        if not raw:
            raise ValidationError('Phone number is required.')
        try:
            parsed = phonenumbers.parse(raw, None)
        except phonenumbers.phonenumberutil.NumberParseException:
            raise ValidationError(
                'Enter a valid international phone number (e.g. +919876543210).'
            )
        if not phonenumbers.is_valid_number(parsed):
            raise ValidationError(
                'This phone number is not valid. '
                'Please include the country code in E.164 format.'
            )
        return phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.E164
        )


# ---------------------------------------------------------------------------
# NotificationTemplateForm
# ---------------------------------------------------------------------------

class NotificationTemplateForm(forms.ModelForm):
    class Meta:
        model = NotificationTemplate
        fields = ['title', 'channel', 'body', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': 'e.g. Post-Sale Thank You',
            }),
            'channel': forms.Select(attrs={'class': _SELECT_CLASS}),
            'body': forms.Textarea(attrs={
                'class': _TEXTAREA_CLASS,
                'rows': 5,
                'placeholder': (
                    'Hi {customer_name}, thank you for purchasing '
                    '{product_name}! Your order total is ₹{total_amount}.'
                ),
            }),
            'is_active': forms.CheckboxInput(attrs={'class': _CHECKBOX_CLASS}),
        }
        help_texts = {
            'body': (
                'Available placeholders: '
                '<code>{customer_name}</code>, <code>{product_name}</code>, '
                '<code>{quantity}</code>, <code>{total_amount}</code>, '
                '<code>{status}</code>'
            ),
        }


# ---------------------------------------------------------------------------
# CRMSettingsForm
# ---------------------------------------------------------------------------

class CRMSettingsForm(forms.ModelForm):
    class Meta:
        model = CRMSettings
        fields = ['auto_send_enabled']
        widgets = {
            'auto_send_enabled': forms.CheckboxInput(
                attrs={'class': _CHECKBOX_CLASS}
            ),
        }
