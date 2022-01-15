import copy

from django import forms
from django.conf import settings
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from foodcartapp.models import Product
from foodcartapp.models import Restaurant
from foodcartapp.models import RestaurantMenuItem
from foodcartapp.models import Order

import requests
from geopy import distance


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    default_availability = {restaurant.id: False for restaurant in restaurants}
    products_with_restaurants = []
    for product in products:

        availability = {
            **default_availability,
            **{item.restaurant_id: item.availability for item in product.menu_items.all()},
        }
        orderer_availability = [availability[restaurant.id] for restaurant in restaurants]

        products_with_restaurants.append(
            (product, orderer_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurants': products_with_restaurants,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


def fetch_coordinates(apikey, address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lat, lon


def add_distance_to_restaurant(restaurants, order_coordinates):
    restaurants_with_distances = []

    for restaurant in restaurants:
        restaurant_coordinates = fetch_coordinates(
            settings.YANDEX_GEOCODER_TOKEN,
            restaurant.address
        )

        restaurant.distance_to_order_address = round(
            distance.distance(restaurant_coordinates, order_coordinates).km, 3
        )

        restaurant_copy = copy.copy(restaurant)

        restaurants_with_distances.append(restaurant_copy)

    sorted_restaurants_with_distances = sorted(
        restaurants_with_distances,
        key=lambda restaurant: restaurant.distance_to_order_address
    )

    return sorted_restaurants_with_distances


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = Order.objects.filter(is_processed=False) \
                          .prefetch_related('order_products', 'order_products__product') \
                          .count_price()

    restaurant_menu_items = RestaurantMenuItem.objects.select_related('product', 'restaurant')

    for order in orders:
        order.coordinates = fetch_coordinates(
            settings.YANDEX_GEOCODER_TOKEN,
            order.address
        )

        restaurants_that_can_prepare_order_by_products = []
        for order_product in order.order_products.all():
            restaurants_with_required_product_in_menu = [restaurant_menu_item.restaurant for restaurant_menu_item in restaurant_menu_items if restaurant_menu_item.product==order_product.product]
            restaurants_that_can_prepare_order_by_products.append(restaurants_with_required_product_in_menu)

        restaurants_that_can_prepare_order = set.intersection(*map(set, restaurants_that_can_prepare_order_by_products))

        restaurants_with_distance = add_distance_to_restaurant(
            restaurants_that_can_prepare_order,
            order.coordinates
        )

        order.restaurants = restaurants_with_distance

    return render(request, template_name='order_items.html', context={
        'orders': orders,
    })
