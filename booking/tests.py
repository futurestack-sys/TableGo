from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Reservation, Restaurant, Table


class ReservationCustomerNameTests(TestCase):
    def test_customer_name_is_saved_when_reservation_is_confirmed(self):
        customer = User.objects.create_user(username="booking_customer", password="test-pass")
        restaurant = Restaurant.objects.create(name="Test Restaurant", slug="test-restaurant", cuisine="Test")
        table = Table.objects.create(restaurant=restaurant, name="T1", seats=4)
        self.client.force_login(customer)

        url = reverse("restaurant", args=[restaurant.slug])
        details = {
            "customer_name": "Test Guest",
            "date": (timezone.localdate() + timedelta(days=1)).isoformat(),
            "time": "18:00",
            "guests": "2",
        }
        response = self.client.post(url, details)
        self.assertContains(response, "Table Selection")

        response = self.client.get(url, {**{key: value for key, value in details.items() if key != "customer_name"}, "table": table.pk})
        self.assertContains(response, "Test Guest")
        self.assertNotIn("customer_name", response.wsgi_request.GET)

        response = self.client.post(url, {
            "confirm": "1",
            "date": details["date"],
            "time": details["time"],
            "guests": details["guests"],
            "table": str(table.pk),
        })

        self.assertRedirects(response, reverse("my"))
        reservation = Reservation.objects.get(customer=customer, restaurant=restaurant)
        self.assertEqual(reservation.customer_name, "Test Guest")