# Generated by Django 3.2 on 2022-01-08 10:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0048_auto_20220108_0943'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(choices=[('Epayment', 'Электронно'), ('Cash', 'Наличностью')], db_index=True, default='Epayment', max_length=50, verbose_name='способ оплаты'),
        ),
    ]
