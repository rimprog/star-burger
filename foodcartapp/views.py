import json

from django.http import JsonResponse
from django.templatetags.static import static

from .models import Product
from .models import Order
from .models import OrderItems

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

import phonenumbers


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            },
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def validate_products(order_raw):
    is_valid = True

    try:
        products = order_raw['products']

        if not isinstance(products, list):
            is_valid = False
        elif not products:
            is_valid = False

    except KeyError:
        is_valid = False

    return is_valid


def validate_product_in_products(order_raw):
    is_valid = True

    try:
        for product_raw in order_raw['products']:
            product = Product.objects.get(id=product_raw['product'])

    except Product.DoesNotExist:
        is_valid = False

    return is_valid


def validate_phonenumber(order_raw):
    is_valid = True

    try:
        phonenumber = phonenumbers.parse(order_raw['phonenumber'], 'RU')

        if not phonenumbers.is_valid_number(phonenumber):
            is_valid = False

    except KeyError:
        is_valid = False

    except phonenumbers.phonenumberutil.NumberParseException:
        is_valid = False

    return is_valid


def validate_string_input(order_raw, key):
    is_valid = True

    try:
        string_input = order_raw[key]

        if not isinstance(string_input, str):
            is_valid = False

    except KeyError:
        is_valid = False

    return is_valid


def validate_order_raw(order_raw):
    is_valid = True
    content = {}

    if not validate_products(order_raw):
        is_valid = False
        content = {'error': 'products key not presented or not list'}
    elif not validate_product_in_products(order_raw):
        is_valid = False
        content = {'error': 'product does not exist'}
    elif not validate_phonenumber(order_raw):
        is_valid = False
        content = {'error': 'phonenumber key not presented or not valid (Required phonenumber format: +79999000565)'}
    elif not validate_string_input(order_raw, 'firstname'):
        is_valid = False
        content = {'error': 'firstname key not presented or not str'}
    elif not validate_string_input(order_raw, 'lastname'):
        is_valid = False
        content = {'error': 'lastname key not presented or not str'}
    elif not validate_string_input(order_raw, 'address'):
        is_valid = False
        content = {'error': 'address key not presented or not str'}

    return is_valid, content


@api_view(['POST'])
def register_order(request):
    order_raw = request.data

    is_valid, content = validate_order_raw(order_raw)
    if not is_valid:
        return Response(content, status=status.HTTP_403_FORBIDDEN)

    order = Order.objects.create(
        address=order_raw['address'],
        name=order_raw['firstname'],
        surname=order_raw['lastname'],
        phone=order_raw['phonenumber']
    )

    for product_raw in order_raw['products']:
        product = Product.objects.get(id=product_raw['product'])

        OrderItems.objects.create(
            order=order,
            product=product,
            count=product_raw['quantity']
        )

    content = {'order': order_raw}

    return Response(content, status=status.HTTP_200_OK)
