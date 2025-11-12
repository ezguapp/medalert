from django import forms
from .models import PerfilUsuario

class PerfilUsuarioForm(forms.ModelForm):
    class Meta:
        model = PerfilUsuario
        fields = ['peso_kg', 'altura_cm', 'sexo', 'nivel_actividad']
        widgets = {
            'sexo': forms.Select(attrs={'class': 'form-select'}),
            'nivel_actividad': forms.Select(attrs={'class': 'form-select'}),
            'peso_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'altura_cm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }