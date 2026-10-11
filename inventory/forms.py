from django import forms

from .models import StockMovement


class StockMovementForm(forms.ModelForm):

    class Meta:
        model = StockMovement
        fields = ['product', 'movement_type', 'quantity', 'description']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'movement_type': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'description': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Ej: compra a proveedor, merma, conteo físico'}),
        }
