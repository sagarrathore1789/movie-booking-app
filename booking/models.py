from django.db import models
from django.contrib.auth.models import User


class Movie(models.Model):
    CATEGORY_CHOICES = [
        ('MOVIES', 'Movies'),
        ('MUSIC', 'Music'),
        ('COMEDY', 'Comedy'),
        ('PLAYS', 'Plays'),
        ('WORKSHOPS', 'Workshops'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField()
    genre = models.CharField(max_length=100)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    release_date = models.DateField()
    poster_url = models.URLField(blank=True)

    def __str__(self):
        return self.title


class Theatre(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    address = models.TextField()

    def __str__(self):
        return f"{self.name} - {self.city}"


class Screen(models.Model):
    theatre = models.ForeignKey(Theatre, on_delete=models.CASCADE, related_name="screens")
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.theatre.name} - {self.name}"


class Show(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="shows")
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, related_name="shows")
    show_date = models.DateField()
    show_time = models.TimeField()
    ticket_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.movie.title} - {self.show_date} {self.show_time}"


class Seat(models.Model):
    CATEGORY_CHOICES = [
        ('PRIME', 'Prime Rows'),
        ('CLASSIC_PLUS', 'Classic Plus Rows'),
        ('CLASSIC', 'Classic Rows'),
    ]
    
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name="seats")
    seat_number = models.CharField(max_length=10)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='CLASSIC')
    price = models.DecimalField(max_digits=8, decimal_places=2, default=149.00)
    is_booked = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["show", "seat_number"], name="unique_seat_per_show")
        ]
        ordering = ["seat_number"]

    def __str__(self):
        return f"{self.show} - {self.seat_number} ({self.category})"


class Booking(models.Model):
    STATUS_CHOICES = [("CONFIRMED", "Confirmed"), ("CANCELLED", "Cancelled")]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="movie_bookings")
    seats = models.ManyToManyField(Seat, related_name="bookings")
    booked_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="CONFIRMED")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Booking #{self.pk} - {self.user.username}"