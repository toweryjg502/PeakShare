from django.urls import path

from . import views

urlpatterns = [
    path('', views.my_bookings, name='my_bookings'),
    path('request/<int:item_pk>/', views.booking_request, name='booking_request'),
    path('blackouts/<int:item_pk>/', views.blackout_manage, name='blackout_manage'),
    path('blackouts/delete/<int:pk>/', views.blackout_delete, name='blackout_delete'),
    path('<int:pk>/<slug:action>/', views.booking_action, name='booking_action'),
]