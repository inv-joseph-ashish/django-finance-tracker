from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0019_add_payment_source_to_settlement"),
    ]

    operations = [
        migrations.AlterField(
            model_name="expense",
            name="payment_source",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Selected payment instrument PK (PaymentSource or CreditCard based on payment method).",
                null=True,
            ),
        ),
    ]


