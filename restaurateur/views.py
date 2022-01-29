import copy

from django import forms
from django.conf import settings
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import FieldError

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from foodcartapp.models import Product
from foodcartapp.models import Restaurant
from foodcartapp.models import RestaurantMenuItem
from foodcartapp.models import Order

from geocoderapp.models import Place

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


def fetch_place(address):
    place_coordinates = fetch_coordinates(
        settings.YANDEX_GEOCODER_TOKEN,
        address
    )

    if place_coordinates:
        lat, lon = place_coordinates
        place = Place(
            address=address,
            latitude=lat,
            longitude=lon,
            refreshed_at=timezone.now()
        )

        return place


def find_not_created_places_for_items_with_addresses(items):
    places_addresses = Place.objects.values('address')

    try:
        not_created_places_for_items = items.exclude(address__in=places_addresses)
        not_created_places_addresses = not_created_places_for_items.values('address').distinct()
    except FieldError:
        not_created_places_for_items = items.exclude(restaurant__address__in=places_addresses)
        not_created_places_addresses = not_created_places_for_items.values('restaurant__address').distinct()

    return not_created_places_addresses


def bulk_create_places_by_addresses(place_addresses):
    places = []
    for place_address in place_addresses:
        try:
            place = fetch_place(place_address['address'])
        except KeyError:
            place = fetch_place(place_address['restaurant__address'])

        if place:
            places.append(place)

    created_places = Place.objects.bulk_create(places)

    return created_places


def add_distance_to_restaurant(restaurants, order_coordinates, places):
    restaurants_with_distances = []

    for restaurant in restaurants:
        place = list(
            filter(
                lambda place: place.address == restaurant.address,
                places
            )
        )[0]
        restaurant_coordinates = (place.latitude, place.longitude)

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


def find_restaurants_that_can_prepare_order(order, restaurant_menu_items):
    restaurants_that_can_prepare_order_by_products = []
    for order_product in order.order_products.all():
        restaurants_with_required_product_in_menu = [restaurant_menu_item.restaurant for restaurant_menu_item in restaurant_menu_items if restaurant_menu_item.product==order_product.product]
        restaurants_that_can_prepare_order_by_products.append(restaurants_with_required_product_in_menu)

    restaurants_that_can_prepare_order = set.intersection(*map(set, restaurants_that_can_prepare_order_by_products))

    return restaurants_that_can_prepare_order


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = Order.objects.filter(is_processed=False) \
                          .prefetch_related('order_products', 'order_products__product') \
                          .count_price()

    restaurant_menu_items = RestaurantMenuItem.objects.filter(availability=True).select_related('product', 'restaurant')

    not_created_places_addresses = find_not_created_places_for_items_with_addresses(orders)
    bulk_create_places_by_addresses(not_created_places_addresses)

    not_created_places_addresses = find_not_created_places_for_items_with_addresses(restaurant_menu_items)
    bulk_create_places_by_addresses(not_created_places_addresses)

    places = Place.objects.all()

    for order in orders:
        try:
            place = list(
                filter(
                    lambda place: place.address == order.address,
                    places
                )
            )[0]

            order.coordinates = (place.latitude, place.longitude)

            restaurants_that_can_prepare_order = find_restaurants_that_can_prepare_order(
                order,
                restaurant_menu_items
            )

            restaurants_with_distance = add_distance_to_restaurant(
                restaurants_that_can_prepare_order,
                order.coordinates,
                places
            )

            order.restaurants = restaurants_with_distance

        except IndexError:
            order.restaurants = 'coordinates_error'

    return render(request, template_name='order_items.html', context={
        'orders': orders,
    })
