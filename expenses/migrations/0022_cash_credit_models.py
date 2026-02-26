# Generated manually for Cash Credit module

from decimal import Decimal
import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('expenses', '0021_expense_paid_to_credit_card_alter_expense_amount'),
    ]

    operations = [
        migrations.CreateModel(
            name='CashCredit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('credit_type', models.CharField(choices=[('lent', 'I lent (gave credit to friend)'), ('borrowed', 'I borrowed (received from friend)')], max_length=20)),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('date', models.DateField()),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('friend', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cash_credits', to='expenses.friend')),
                ('given_from_account', models.ForeignKey(blank=True, help_text='Account/cash the loan was given from (lent only).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cash_credit_given_from', to='expenses.paymentsource')),
                ('received_into_account', models.ForeignKey(blank=True, help_text='Account where money was received (borrowed) or where repayments are received (lent).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cash_credit_received', to='expenses.paymentsource')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cash_credits', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CashCreditRepayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('date', models.DateField()),
                ('notes', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cash_credit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='repayments', to='expenses.cashcredit')),
                ('received_into_account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cash_credit_repayments_received', to='expenses.paymentsource')),
            ],
            options={
                'ordering': ['-date', '-created_at'],
            },
        ),
    ]
