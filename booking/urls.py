from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("", views.home, name="home"),
    path("movie/<int:movie_id>/", views.movie_detail, name="movie_detail"),
    path("show/<int:show_id>/seats/", views.seat_selection, name="seat_selection"),
    path("show/<int:show_id>/generate-seats/", views.generate_seats, name="generate_seats"),
    path("my-bookings/", views.my_bookings, name="my_bookings"),
    
    # Login / Logout / Signup URLs
    path("login/", auth_views.LoginView.as_view(template_name="booking/login.html"), name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("signup/", views.signup, name="signup"),
]