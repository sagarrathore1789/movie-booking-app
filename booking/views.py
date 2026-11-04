from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout as auth_logout
from datetime import date, timedelta

from .models import Movie, Show, Seat, Booking


# ==========================================
# 1. HOME PAGE (Search + Category Filter)
# ==========================================
def home(request):
    movies = Movie.objects.all()
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    if query:
        movies = movies.filter(title__icontains=query)
    if category:
        movies = movies.filter(category=category)

    return render(request, "booking/home.html", {
        "movies": movies,
        "query": query,
        "selected_category": category
    })


# ==========================================
# 2. MOVIE DETAIL (Date Filter + Showtimes)
# ==========================================
def movie_detail(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    
    # Date filter logic
    selected_date_str = request.GET.get('date')
    if selected_date_str:
        selected_date = selected_date_str
    else:
        # Default aaj ki date
        selected_date = date.today().strftime('%Y-%m-%d')

    # Shows ko filter karo us date ke hisaab se
    shows = movie.shows.filter(show_date=selected_date).select_related("screen__theatre")
    
    # 5 din ki dates generate karo (aaj se 5 din tak)
    dates = []
    for i in range(5):
        d = date.today() + timedelta(days=i)
        dates.append({
            'value': d.strftime('%Y-%m-%d'),
            'day': d.strftime('%a'),
            'date': d.strftime('%d'),
            'month': d.strftime('%b'),
        })

    return render(request, "booking/movie_detail.html", {
        "movie": movie, 
        "shows": shows,
        "dates": dates,
        "selected_date": selected_date
    })


# ==========================================
# 3. SIGNUP (New User Registration)
# ==========================================
def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Signup ke baad direct login
            messages.success(request, "Account created successfully! Welcome.")
            return redirect("home")
    else:
        form = UserCreationForm()
    return render(request, "booking/signup.html", {"form": form})


# ==========================================
# 4. CUSTOM LOGOUT (Fixes 405 Error)
# ==========================================
def user_logout(request):
    auth_logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("home")


# ==========================================
# 5. SEAT SELECTION & BOOKING
# ==========================================
@login_required
def seat_selection(request, show_id):
    show = get_object_or_404(Show.objects.select_related("movie", "screen__theatre"), id=show_id)
    all_seats = Seat.objects.filter(show=show).order_by("seat_number")

    if request.method == "POST":
        selected_ids = request.POST.getlist("seats")

        if not selected_ids:
            messages.error(request, "Please select at least one seat.")
            return redirect("seat_selection", show_id=show.id)

        with transaction.atomic():
            available_seats = Seat.objects.select_for_update().filter(
                show=show, id__in=selected_ids, is_booked=False
            )

            if available_seats.count() != len(set(selected_ids)):
                messages.error(request, "Some selected seats are no longer available.")
                return redirect("seat_selection", show_id=show.id)

            # Total price calculate karo (har seat ka apna price)
            total = sum(seat.price for seat in available_seats)

            booking = Booking.objects.create(
                user=request.user,
                total_amount=total,
                status="CONFIRMED"
            )
            booking.seats.set(available_seats)
            available_seats.update(is_booked=True)

        messages.success(request, "Booking Confirmed!")
        return render(request, "booking/booking_success.html", {"booking": booking})

    # Seats ko categories me divide karo
    prime_seats = [s for s in all_seats if s.category == 'PRIME']
    classic_plus_seats = [s for s in all_seats if s.category == 'CLASSIC_PLUS']
    classic_seats = [s for s in all_seats if s.category == 'CLASSIC']

    context = {
        "show": show,
        "prime_seats": prime_seats,
        "classic_plus_seats": classic_plus_seats,
        "classic_seats": classic_seats,
    }
    return render(request, "booking/seat_selection.html", context)


# ==========================================
# 6. GENERATE SEATS (Admin Only)
# ==========================================
@staff_member_required
def generate_seats(request, show_id):
    show = get_object_or_404(Show, id=show_id)

    if request.method == "POST":
        try:
            total_seats = int(request.POST.get("total_seats", 0))
            seats_per_row = int(request.POST.get("seats_per_row", 15))
        except (TypeError, ValueError):
            messages.error(request, "Invalid input.")
            return redirect("generate_seats", show_id=show.id)

        if total_seats < 1 or total_seats > 500 or seats_per_row < 1 or seats_per_row > 50:
            messages.error(request, "Please enter valid numbers.")
            return redirect("generate_seats", show_id=show.id)

        if show.seats.exists():
            messages.error(request, "Seats already exist for this show.")
            return redirect("generate_seats", show_id=show.id)

        seats = []
        for number in range(1, total_seats + 1):
            row_letter = chr(65 + (number - 1) // seats_per_row)
            seat_in_row = (number - 1) % seats_per_row + 1
            seat_number = f"{row_letter}{seat_in_row}"
            
            # Auto-Assign Categories (A-B: Prime, C-G: Classic Plus, Baaki: Classic)
            if row_letter in ['A', 'B']:
                cat = 'PRIME'
            elif row_letter in ['C', 'D', 'E', 'F', 'G']:
                cat = 'CLASSIC_PLUS'
            else:
                cat = 'CLASSIC'
                
            seats.append(Seat(show=show, seat_number=seat_number, category=cat, price=149.00))

        Seat.objects.bulk_create(seats)
        messages.success(request, f"{total_seats} seats created successfully!")
        return redirect("generate_seats", show_id=show.id)

    return render(request, "booking/generate_seats.html", {"show": show, "seat_count": show.seats.count()})


# ==========================================
# 7. MY BOOKINGS & CANCEL TICKET
# ==========================================
@login_required
def my_bookings(request):
    # Sirf us user ki bookings nikalo
    bookings = Booking.objects.filter(user=request.user).order_by("-booked_at")
    
    if request.method == "POST":
        booking_id = request.POST.get("booking_id")
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        
        if booking.status == "CONFIRMED":
            with transaction.atomic():
                # Seats ko wapas available karo
                seats = booking.seats.all()
                seats.update(is_booked=False)
                
                # Booking cancel karo
                booking.status = "CANCELLED"
                booking.save()
                
            messages.success(request, "Ticket cancelled successfully.")
            return redirect("my_bookings")

    return render(request, "booking/my_bookings.html", {"bookings": bookings})