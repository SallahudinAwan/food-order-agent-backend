from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "category", "is_available"]

class AddCartItemSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=100)
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)

class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)

class SessionSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=100)
    customer_id = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")

class AgentMessageSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=100)
    customer_id = serializers.CharField(max_length=100)
    message = serializers.CharField(max_length=1000, allow_blank=False, trim_whitespace=True)
    language = serializers.ChoiceField(choices=["auto", "en-PK", "ur-PK"], required=False, default="auto")

class CustomerSerializer(serializers.Serializer):
    customer_id = serializers.CharField(max_length=100)

class SpeechSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)
    language = serializers.ChoiceField(choices=["en-PK", "ur-PK"])
