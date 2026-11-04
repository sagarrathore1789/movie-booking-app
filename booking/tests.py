from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from .models import Movie, Theatre, Screen, Show, Seat, Booking


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_movie(title="Test Movie", **kwargs):
    defaults = {
        "description": "A test movie.",
        "genre": "Action",
        "duration": 120,
        "release_date": date(2024, 1, 1),
    }
    defaults.update(kwargs)
    return Movie.objects.create(title=title, **defaults)


def make_theatre(name="Test Theatre", city="Mumbai"):
    return Theatre.objects.create(
        name=name,
        city=city,
        address="Test Address",
    )


def make_screen(theatre=None, name="Screen 1"):
    if theatre is None:
        theatre = make_theatre()
    return Screen.objects.create(theatre=theatre, name=name)


def make_show(movie=None, screen=None, price=Decimal("250.00")):
    if movie is None:
        movie = make_movie()
    if screen is None:
        screen = make_screen()
    return Show.objects.create(
        movie=movie,
        screen=screen,
        show_date=date(2024, 6, 1),
        show_time=time(19, 30),
        ticket_price=price,
    )


# ---------------------------------------------------------------------------
# Home / Search
# ---------------------------------------------------------------------------
class HomeViewTests(TestCase):
    def test_home_lists_all_movies(self):
        make_movie("Inception")
        make_movie("Interstellar")
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inception")
        self.assertContains(response, "Interstellar")

    def test_search_filters_movies(self):
        make_movie("Inception")
        make_movie("Interstellar")
        make_movie("The Dark Knight")

        response = self.client.get(reverse("home"), {"q": "incept"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inception")
        self.assertNotContains(response, "The Dark Knight")

    def test_search_is_case_insensitive(self):
        make_movie("Inception")
        response = self.client.get(reverse("home"), {"q": "INCEPTION"})
        self.assertContains(response, "Inception")

    def test_search_no_results_message(self):
        make_movie("Inception")
        response = self.client.get(reverse("home"), {"q": "zzzzz"})
        self.assertContains(response, "No matching movies found")

    def test_empty_search_returns_all(self):
        make_movie("Inception")
        make_movie("Interstellar")
        response = self.client.get(reverse("home"), {"q": ""})
        self.assertContains(response, "Inception")
        self.assertContains(response, "Interstellar")


# ---------------------------------------------------------------------------
# Movie detail
# ---------------------------------------------------------------------------
class MovieDetailViewTests(TestCase):
    def test_movie_detail_shows_shows(self):
        movie = make_movie()
        theatre = make_theatre(name="PVR Cinemas")
        screen = make_screen(theatre=theatre, name="Audi 1")
        make_show(movie=movie, screen=screen)

        response = self.client.get(reverse("movie_detail", args=[movie.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PVR Cinemas")
        self.assertContains(response, "Audi 1")

    def test_movie_detail_404_for_unknown_movie(self):
        response = self.client.get(reverse("movie_detail", args=[9999]))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Seat generation (staff only)
# ---------------------------------------------------------------------------
class GenerateSeatsTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="admin", password="pass", is_staff=True
        )
        self.show = make_show()

    def test_non_staff_cannot_generate(self):
        self.client.login(username="admin", password="pass")
        # logout then hit url as anonymous
        self.client.logout()
        response = self.client.get(
            reverse("generate_seats", args=[self.show.id])
        )
        # staff_member_required redirects to admin login
        self.assertEqual(response.status_code, 302)

    def test_staff_generates_150_seats_in_rows_of_15(self):
        self.client.login(username="admin", password="pass")
        response = self.client.post(
            reverse("generate_seats", args=[self.show.id]),
            {"total_seats": 150, "seats_per_row": 15},
        )
        self.assertEqual(response.status_code, 302)  # redirect after POST

        seats = Seat.objects.filter(show=self.show)
        self.assertEqual(seats.count(), 150)

        # First seat = A1, 15th seat = A15, 16th seat = B1
        self.assertEqual(seats.get(seat_number="A1").seat_number, "A1")
        self.assertEqual(seats.get(seat_number="A15").seat_number, "A15")
        self.assertEqual(seats.get(seat_number="B1").seat_number, "B1")
        self.assertEqual(seats.get(seat_number="J15").seat_number, "J15")

    def test_cannot_generate_twice(self):
        self.client.login(username="admin", password="pass")
        url = reverse("generate_seats", args=[self.show.id])
        self.client.post(url, {"total_seats": 10, "seats_per_row": 5})
        self.client.post(url, {"total_seats": 10, "seats_per_row": 5})
        # Still 10 seats, not 20
        self.assertEqual(Seat.objects.filter(show=self.show).count(), 10)

    def test_rejects_invalid_total_seats(self):
        self.client.login(username="admin", password="pass")
        url = reverse("generate_seats", args=[self.show.id])
        self.client.post(url, {"total_seats": 0, "seats_per_row": 15})
        self.assertEqual(Seat.objects.filter(show=self.show).count(), 0)

    def test_rejects_more_than_500_seats(self):
        self.client.login(username="admin", password="pass")
        url = reverse("generate_seats", args=[self.show.id])
        self.client.post(url, {"total_seats": 501, "seats_per_row": 15})
        self.assertEqual(Seat.objects.filter(show=self.show).count(), 0)


# ---------------------------------------------------------------------------
# Seat selection + booking flow
# ---------------------------------------------------------------------------
class SeatSelectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", password="pass"
        )
        self.show = make_show(price=Decimal("250.00"))
        # 4 seats: A1, A2, A3, A4
        for n in ["A1", "A2", "A3", "A4"]:
            Seat.objects.create(show=self.show, seat_number=n)

    def _login(self):
        self.client.login(username="alice", password="pass")

    def test_login_required(self):
        url = reverse("seat_selection", args=[self.show.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_get_shows_seats(self):
        self._login()
        response = self.client.get(
            reverse("seat_selection", args=[self.show.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A1")
        self.assertContains(response, "A4")

    def test_booking_creates_booking_and_marks_seats(self):
        self._login()
        seats = list(Seat.objects.filter(show=self.show).order_by("id")[:2])
        response = self.client.post(
            reverse("seat_selection", args=[self.show.id]),
            {"seats": [str(s.id) for s in seats]},
        )
        self.assertEqual(response.status_code, 200)

        # One booking created
        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.first()
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.total_amount, Decimal("500.00"))
        self.assertEqual(booking.seats.count(), 2)

        # Seats marked booked
        for s in seats:
            s.refresh_from_db()
            self.assertTrue(s.is_booked)

    def test_booking_with_no_seats_shows_error(self):
        self._login()
        response = self.client.post(
            reverse("seat_selection", args=[self.show.id]),
            {},
            follow=True,
        )
        self.assertEqual(Booking.objects.count(), 0)
        self.assertContains(response, "Please select at least one seat")

    def test_cannot_book_already_booked_seat(self):
        self._login()
        seat = Seat.objects.first()
        seat.is_booked = True
        seat.save()

        response = self.client.post(
            reverse("seat_selection", args=[self.show.id]),
            {"seats": [str(seat.id)]},
            follow=True,
        )
        self.assertEqual(Booking.objects.count(), 0)
        self.assertContains(
            response,
            "Some selected seats are no longer available",
        )


# ---------------------------------------------------------------------------
# Model sanity checks
# ---------------------------------------------------------------------------
class ModelTests(TestCase):
    def test_seat_unique_per_show(self):
        show = make_show()
        Seat.objects.create(show=show, seat_number="A1")
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Seat.objects.create(show=show, seat_number="A1")

    def test_movie_str(self):
        m = make_movie("Inception")
        self.assertEqual(str(m), "Inception")

    def test_show_str(self):
        show = make_show()
        self.assertIn(show.movie.title, str(show))