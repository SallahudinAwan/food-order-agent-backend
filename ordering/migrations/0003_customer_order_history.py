from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ordering", "0002_agentconversation")]

    operations = [
        migrations.AddField(
            model_name="agentconversation",
            name="customer_id",
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="customer_id",
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
    ]
