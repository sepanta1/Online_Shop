from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'is_sale', 'sale_price',  'image']

    image = serializers.ImageField(source='image.url')
