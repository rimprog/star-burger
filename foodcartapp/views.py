import json

from django.http import JsonResponse
from django.templatetags.static import static

from .models import Product
from .models import Order
from .models import OrderItems

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


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


def validate_order_raw(order_raw):
    is_valid = True

    try:
        product = order_raw['products']
    except KeyError:
        is_valid = False

        return is_valid

    if isinstance(product, str):
        is_valid = False
    elif product is None:
        is_valid = False
    elif isinstance(product, list) and not product:
        is_valid = False

    return is_valid


@api_view(['POST'])
def register_order(request):
    order_raw = request.data
    is_valid = validate_order_raw(order_raw)

    if not is_valid:
        content = {'error': 'products key not presented or not list'}

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
