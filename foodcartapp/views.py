import json

from django.http import JsonResponse
from django.templatetags.static import static

from .models import Product
from .models import Order
from .models import OrderItems


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


def register_order(request):
    try:
        order_raw = json.loads(request.body.decode())

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

        return JsonResponse({
            'status': 'ok'
        })

    except ValueError:
        return JsonResponse({
            'status': 'error',
            'error': 'Order not created',
        })
