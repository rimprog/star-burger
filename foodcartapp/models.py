from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

from phonenumber_field.modelfields import PhoneNumberField


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):
    def count_price(self):
        orders_with_prices = self.annotate(
            price=models.Sum(
                'order_products__price'
            )
        )
        return orders_with_prices


class Order(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('Epayment', 'Электронно'),
        ('Cash', 'Наличностью')
    ]
    IS_PROCESSED_CHOICES = [
        (True, 'Обработан'),
        (False, 'Необработанный')
    ]
    address = models.CharField(
        'адрес',
        max_length=100,
        db_index=True
    )
    firstname = models.CharField(
        'имя',
        max_length=50,
    )
    lastname = models.CharField(
        'фамилия',
        max_length=50,
    )
    phonenumber = PhoneNumberField(
        'мобильный номер',
        db_index=True
    )
    payment_method = models.CharField(
        'способ оплаты',
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        default='Epayment',
        db_index=True
    )
    is_processed = models.BooleanField(
        'заказ обработан',
        choices=IS_PROCESSED_CHOICES,
        default=False,
        db_index=True
    )
    comment = models.TextField(
        'комментарий',
        default='',
        blank=True,
        null=True,
    )
    registrated_at = models.DateTimeField(
        'Когда зарегистрирован',
        default=timezone.now,
        blank=True,
        null=True,
        db_index=True
    )
    called_at = models.DateTimeField(
        'Когда обзвонен',
        default=None,
        blank=True,
        null=True,
        db_index=True
    )
    delivered_at = models.DateTimeField(
        'Когда доставлен',
        default=None,
        blank=True,
        null=True,
        db_index=True
    )
    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name='ресторан',
        related_name='orders',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        default=None
    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return self.address


class OrderProduct(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='order_products',
        verbose_name="заказ",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='order_products',
        verbose_name='товар',
    )
    quantity = models.PositiveIntegerField(
        'количество',
        validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        'цена',
        validators=[MinValueValidator(1)],
        max_digits=8,
        decimal_places=2,
        default=None,
        null=True
    )

    class Meta:
        verbose_name = 'товар в заказе'
        verbose_name_plural = 'товары в заказе'
        unique_together = [
            ['order', 'product']
        ]

    def count_price(self):
        price = self.product.price * self.quantity

        return price

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"
