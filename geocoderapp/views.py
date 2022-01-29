import copy

from django.shortcuts import render
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import FieldError

from geocoderapp.models import Place

import requests
from geopy import distance


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
