import copy

from geopy import distance


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


def append_restaurants_with_distance_to_order(order, places, restaurant_menu_items):
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

    return order
