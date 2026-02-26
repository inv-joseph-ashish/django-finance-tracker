# Add paid_from_account to CashCreditRepayment (for borrowed repayments)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0022_cash_credit_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='cashcreditrepayment',
            name='paid_from_account',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cash_credit_repayments_paid_from',
                to='expenses.paymentsource',
            ),
        ),
    ]
