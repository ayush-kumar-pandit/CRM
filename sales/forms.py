import phonenumbers
from django import forms
from django.core.exceptions import ValidationError
from .models import CRMSettings, NotificationTemplate, Sale

_INPUT = 'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'
_SELECT = 'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'
_TEXTAREA = 'block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-y'
_CHECKBOX = 'h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500'


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer_name', 'email', 'phone_number', 'product_name', 'quantity', 'price', 'shipping_address', 'status', 'notes']
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': _INPUT}),
            'email': forms.EmailInput(attrs={'class': _INPUT}),
            'phone_number': forms.TextInput(attrs={'class': _INPUT, 'placeholder': '+919876543210'}),
            'product_name': forms.TextInput(attrs={'class': _INPUT}),
            'quantity': forms.NumberInput(attrs={'class': _INPUT, 'min': 1}),
            'price': forms.NumberInput(attrs={'class': _INPUT, 'step': '0.01'}),
            'shipping_address': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 3}),
            'status': forms.Select(attrs={'class': _SELECT}),
            'notes': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 2}),
        }

    def clean_phone_number(self):
        raw = self.cleaned_data.get('phone_number', '').strip()
        try:
            parsed = phonenumbers.parse(raw, None)
        except phonenumbers.NumberParseException:
            raise ValidationError('Enter a valid international phone number.')
        if not phonenumbers.is_valid_number(parsed):
            raise ValidationError('Phone number is not valid.')
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


class NotificationTemplateForm(forms.ModelForm):
    class Meta:
        model = NotificationTemplate
        fields = ['title', 'channel', 'body', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': _INPUT}),
            'channel': forms.Select(attrs={'class': _SELECT}),
            'body': forms.Textarea(attrs={'class': _TEXTAREA, 'rows': 5}),
            'is_active': forms.CheckboxInput(attrs={'class': _CHECKBOX}),
        }


class CRMSettingsForm(forms.ModelForm):
    class Meta:
        model = CRMSettings
        fields = ['auto_send_enabled']
        widgets = {'auto_send_enabled': forms.CheckboxInput(attrs={'class': _CHECKBOX})}
