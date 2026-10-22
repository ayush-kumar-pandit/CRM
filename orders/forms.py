"""
Forms for the Orders app.

ClientForm  — Quick-add a new client inline on the order entry page
ProductForm — Add / edit a product (for admin-style product management)
"""

import phonenumbers
from django import forms
from django.core.exceptions import ValidationError

from .models import Client, Product

# ---------------------------------------------------------------------------
# Shared Tailwind widget classes
# ---------------------------------------------------------------------------

_INPUT = (
    'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 '
    'text-sm text-slate-900 shadow-sm placeholder:text-slate-400 '
    'focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'
)
_SELECT = (
    'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 '
    'text-sm text-slate-900 shadow-sm focus:border-indigo-500 '
    'focus:outline-none focus:ring-1 focus:ring-indigo-500'
)
_TEXTAREA = (
    'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 '
    'text-sm text-slate-900 shadow-sm placeholder:text-slate-400 '
    'focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-y'
)
_CHECKBOX = 'h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500'


# ---------------------------------------------------------------------------
# ClientForm
# ---------------------------------------------------------------------------

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'phone_number', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Full name'}),
            'phone_number': forms.TextInput(attrs={
                'class': _INPUT,
                'placeholder': '+919876543210',
            }),
            'email': forms.EmailInput(attrs={'class': _INPUT, 'placeholder': 'client@example.com'}),
        }
        help_texts = {
            'phone_number': 'Include country code, e.g. +919876543210',
        }

    def clean_phone_number(self):
        raw = self.cleaned_data.get('phone_number', '').strip()
        if not raw:
            raise ValidationError('Phone number is required.')
        try:
            parsed = phonenumbers.parse(raw, None)
        except phonenumbers.NumberParseException:
            raise ValidationError('Enter a valid international phone number (e.g. +919876543210).')
        if not phonenumbers.is_valid_number(parsed):
            raise ValidationError('This phone number is not valid.')
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


# ---------------------------------------------------------------------------
# ProductForm
# ---------------------------------------------------------------------------

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'stock_quantity', 'price', 'is_restocked']
        widgets = {
            'name': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Product name'}),
            'description': forms.Textarea(attrs={
                'class': _TEXTAREA, 'rows': 2, 'placeholder': 'Optional description…',
            }),
            'stock_quantity': forms.NumberInput(attrs={'class': _INPUT, 'min': 0}),
            'price': forms.NumberInput(attrs={'class': _INPUT, 'step': '0.01', 'placeholder': '0.00'}),
            'is_restocked': forms.CheckboxInput(attrs={'class': _CHECKBOX}),
        }
