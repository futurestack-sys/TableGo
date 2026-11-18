from django import forms
from .models import Restaurant, Table


class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ["name", "seats", "shape", "x", "y"]


class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ["name", "slug", "cuisine", "description", "location", "hours"]
