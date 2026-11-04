from django import template

register = template.Library()

@register.filter
def split_seats_by_row(seats):
    rows = {}
    for seat in seats:
        # Seat number se Row nikaalo (jaise "A1" se "A")
        row_letter = ''.join(filter(str.isalpha, seat.seat_number))
        if row_letter not in rows:
            rows[row_letter] = []
        rows[row_letter].append(seat)
    
    # Rows ko alphabetically sort karke return karo
    return sorted(rows.items())