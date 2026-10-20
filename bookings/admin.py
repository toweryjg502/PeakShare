from django.contrib import admin

from .models import BlackoutDate, Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('item', 'renter', 'start_date', 'end_date', 'status', 'total_price')
    list_filter = ('status',)
    search_fields = ('item__title', 'renter__username')


@admin.register(BlackoutDate)
class BlackoutDateAdmin(admin.ModelAdmin):
    list_display = ('item', 'start_date', 'end_date', 'reason')