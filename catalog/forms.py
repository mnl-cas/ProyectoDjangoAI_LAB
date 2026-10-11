from django import forms

from .models import Category, Product, ReferenceImage


class CategoryForm(forms.ModelForm):

  class Meta:
    model = Category
    fields = ['name', 'description']
    widgets = {
        'name': forms.TextInput(attrs={'class': 'form-control'}),
        'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    }


class ProductForm(forms.ModelForm):

  class Meta:
    model = Product
    fields = ['name', 'category', 'price', 'stock', 'min_stock', 'description']
    widgets = {
        'name': forms.TextInput(attrs={'class': 'form-control'}),
        'category': forms.Select(attrs={'class': 'form-select'}),
        'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
        'stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        'min_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        'description': forms.Textarea(
            attrs={'class': 'form-control', 'rows': 3}
        ),
    }


class ReferenceImageForm(forms.ModelForm):

  class Meta:
    model = ReferenceImage
    fields = ['image']
    widgets = {
        'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
    }
