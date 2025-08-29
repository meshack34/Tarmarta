from django import forms
from core.models import Product, PackSize, PriceList, Market, Outlet

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "description", "is_active", "sku"]


class PackSizeForm(forms.ModelForm):
    class Meta:
        model = PackSize
        fields = ["label", "packaging_type", "unit", "sku", "is_active"]


class PriceListForm(forms.ModelForm):
    class Meta:
        model = PriceList
        fields = ["pack", "market", "unit_price", "tax_rate", "discount_policy", "effective_from", "effective_to", "status"]

class MarketForm(forms.ModelForm):
    class Meta:
        model = Market
        fields = ["name", "region", "type", "gps_lat", "gps_long", "status"]


class OutletForm(forms.ModelForm):
    class Meta:
        model = Outlet
        fields = ["market", "name", "owner_name", "contact_phone", "location", "descriptor"]