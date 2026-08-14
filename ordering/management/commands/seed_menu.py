from decimal import Decimal
from django.core.management.base import BaseCommand
from ordering.models import Product

PRODUCTS = [
    ("Zinger Burger", "Crispy spicy chicken fillet with lettuce and mayo.", "650.00", "Burgers"),
    ("Chicken Burger", "Grilled chicken patty with fresh salad.", "500.00", "Burgers"),
    ("Beef Burger", "Seasoned beef patty with cheese and house sauce.", "750.00", "Burgers"),
    ("French Fries", "Golden, lightly salted fries.", "300.00", "Sides"),
    ("Loaded Fries", "Fries topped with cheese, chicken, and sauce.", "500.00", "Sides"),
    ("Pepsi", "Chilled soft drink.", "150.00", "Drinks"), ("Coke", "Chilled soft drink.", "150.00", "Drinks"),
    ("Sprite", "Chilled lemon-lime soft drink.", "150.00", "Drinks"),
    ("Chicken Pizza", "Chicken, mozzarella, peppers, and tomato sauce.", "1200.00", "Pizza"),
    ("BBQ Pizza", "BBQ chicken, onions, mozzarella, and smoky sauce.", "1300.00", "Pizza"),
]
class Command(BaseCommand):
    help = "Create or update the sample menu"
    def handle(self, *args, **options):
        for name, description, price, category in PRODUCTS:
            Product.objects.update_or_create(name=name, defaults={"description": description, "price": Decimal(price), "category": category, "is_available": True})
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(PRODUCTS)} products."))
