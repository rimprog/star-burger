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


def find_not_created_places_for_needed_addresses(needed_addresses):
    created_places_for_needed_addresses = Place.objects.filter(address__in=needed_addresses)
    created_places_addresses_for_needed_addresses = [place.address for place in created_places_for_needed_addresses]
    not_created_places_addresses = [address for address in needed_addresses if address not in created_places_addresses_for_needed_addresses]

    return not_created_places_addresses


def bulk_create_places_by_addresses(place_addresses):
    places = []
    for place_address in place_addresses:
        place = fetch_place(place_address)

        if place:
            places.append(place)

    created_places = Place.objects.bulk_create(places)

    return created_places
