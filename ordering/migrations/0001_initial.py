import decimal
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="Cart", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("session_id", models.CharField(db_index=True, max_length=100, unique=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True))]),
        migrations.CreateModel(name="Product", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=160, unique=True)), ("description", models.TextField(blank=True)), ("price", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.00"))])), ("category", models.CharField(db_index=True, max_length=80)), ("is_available", models.BooleanField(db_index=True, default=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True))]),
        migrations.CreateModel(name="Order", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("order_number", models.CharField(blank=True, max_length=24, null=True, unique=True)), ("status", models.CharField(choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled"), ("completed", "Completed")], default="pending", max_length=20)), ("total", models.DecimalField(decimal_places=2, max_digits=12)), ("source_session_id", models.CharField(max_length=100, unique=True)), ("created_at", models.DateTimeField(auto_now_add=True))]),
        migrations.CreateModel(name="CartItem", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("quantity", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("cart", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="ordering.cart")), ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="ordering.product"))]),
        migrations.CreateModel(name="OrderItem", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("product_name", models.CharField(max_length=160)), ("quantity", models.PositiveIntegerField()), ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)), ("line_total", models.DecimalField(decimal_places=2, max_digits=12)), ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="ordering.order")), ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="ordering.product"))]),
        migrations.AddConstraint(model_name="cartitem", constraint=models.UniqueConstraint(fields=("cart", "product"), name="unique_product_per_cart")),
        migrations.AddConstraint(model_name="cartitem", constraint=models.CheckConstraint(condition=models.Q(("quantity__gte", 1)), name="cart_quantity_positive")),
    ]

