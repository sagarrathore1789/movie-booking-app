from django.contrib import admin
from .models import Movie, Theatre, Screen, Show, Seat, Booking


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "genre", "duration", "release_date")
    search_fields = ("title", "genre")
    list_filter = ("genre",)


@admin.register(Theatre)
class TheatreAdmin(admin.ModelAdmin):
    list_display = ("name", "city")
    search_fields = ("name", "city")
    list_filter = ("city",)


@admin.register(Screen)
class ScreenAdmin(admin.ModelAdmin):
    list_display = ("name", "theatre")
    search_fields = ("name", "theatre__name")
    list_filter = ("theatre",)


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = (
        "movie",
        "screen",
        "show_date",
        "show_time",
        "ticket_price",
    )
    list_filter = ("show_date", "screen__theatre", "movie")
    search_fields = ("movie__title", "screen__theatre__name")
    date_hierarchy = "show_date"


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("id", "show", "seat_number", "is_booked")
    list_filter = ("is_booked", "show")
    search_fields = ("seat_number",)
    ordering = ("show", "seat_number")
    list_per_page = 200


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total_amount", "booked_at")
    list_filter = ("status", "booked_at")
    search_fields = ("user__username",)
    filter_horizontal = ("seats",)
    readonly_fields = ("booked_at",)