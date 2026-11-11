from django.contrib import admin
from django.utils.html import format_html

from .models import BlackoutDate, Booking, BookingAlert, ConditionPhoto


class ConditionPhotoInline(admin.TabularInline):
    model = ConditionPhoto
    extra = 0
    can_delete = False
    fields = ('stage', 'uploaded_by', 'created_at', 'preview')
    readonly_fields = fields

    @admin.display(description='Photo')
    def preview(self, obj):
        if not obj.image:
            return 'No photo'
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">'
            '<img src="{}" alt="Condition photo" style="max-width: 140px; max-height: 110px;">'
            '</a>', obj.image.url, obj.image.url,
        )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'item', 'renter', 'start_date', 'end_date', 'status',
        'payment_status', 'rental_status', 'payout_status', 'total_price',
        'dispute_previous_status', 'dispute_reported_by', 'disputed_at',
        'dispute_summary',
    )
    list_filter = ('status', 'payment_status', 'rental_status', 'payout_status')
    search_fields = ('item__title', 'renter__username', 'dispute_reason')
    inlines = (ConditionPhotoInline,)
    list_select_related = ('item', 'renter', 'dispute_reported_by')

    @admin.display(description='Dispute reason')
    def dispute_summary(self, obj):
        if not obj.dispute_reason:
            return '—'
        return obj.dispute_reason[:90] + ('…' if len(obj.dispute_reason) > 90 else '')


@admin.register(BlackoutDate)
class BlackoutDateAdmin(admin.ModelAdmin):
    list_display = ('item', 'start_date', 'end_date', 'reason')


@admin.register(ConditionPhoto)
class ConditionPhotoAdmin(admin.ModelAdmin):
    list_display = ('booking', 'stage', 'uploaded_by', 'created_at')
    list_filter = ('stage',)


@admin.register(BookingAlert)
class BookingAlertAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'booking', 'kind', 'created_at', 'read_at')
    list_filter = ('kind', 'read_at')
    search_fields = ('recipient__username', 'booking__item__title', 'message')
