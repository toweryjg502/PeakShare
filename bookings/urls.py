from django.urls import path

from . import views

urlpatterns = [
    path('', views.my_bookings, name='my_bookings'),
    path('alerts/', views.booking_alert_list, name='booking_alert_list'),
    path('alerts/status/', views.booking_alert_status, name='booking_alert_status'),
    path('alerts/<int:alert_pk>/open/', views.booking_alert_open, name='booking_alert_open'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('request/<int:item_pk>/', views.booking_request, name='booking_request'),
    path('<int:pk>/checkout/', views.booking_checkout, name='booking_checkout'),
    path('<int:pk>/photo/<slug:stage>/', views.booking_photo_upload, name='booking_photo_upload'),
    path('<int:pk>/rental/<slug:action>/', views.booking_rental_action, name='booking_rental_action'),
    path('blackouts/<int:item_pk>/', views.blackout_manage, name='blackout_manage'),
    path('blackouts/delete/<int:pk>/', views.blackout_delete, name='blackout_delete'),
    path('<int:pk>/<slug:action>/', views.booking_action, name='booking_action'),
]
