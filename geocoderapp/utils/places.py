from django.conf import settings
from django.utils import timezone
from django.core.exceptions import FieldError

from geocoderapp.models import Place
from geocoderapp.utils.yandex_geocoder import fetch_coordinates


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
