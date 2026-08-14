from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ordering", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="AgentConversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_id", models.CharField(db_index=True, max_length=100, unique=True)),
                ("history", models.JSONField(blank=True, default=list)),
                ("reviewed_cart_hash", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
