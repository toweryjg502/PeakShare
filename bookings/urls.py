from django.urls import path

from . import views

urlpatterns = [
    path('', views.my_bookings, name='my_bookings'),
    path('request/<int:item_pk>/', views.booking_request, name='booking_request'),
    path('<int:pk>/<slug:action>/', views.booking_action, name='booking_action'),
]