from django.urls import path
from . import views as v
urlpatterns = [
    path("", v.home, name="home"),
    path("restaurants/", v.restaurants, name="restaurants"),
    path("register/", v.register, name="register"),
    path("restaurant/<slug:slug>/", v.reserve, name="restaurant"),
    path("my/", v.my_reservations, name="my"),
    path("my/cancel/<int:pk>/", v.cancel, name="cancel"),
    path("dashboard/", v.dashboard, name="dashboard"),
    path("dashboard/reservations/", v.d_reservations, name="d_reservations"),
    path("dashboard/reservations/<int:pk>/<str:status>/", v.d_status, name="d_status"),
    path("dashboard/restaurants/", v.d_restaurants, name="d_restaurants"),
    path("dashboard/tables/", v.d_tables, name="d_tables"),
    path("dashboard/customers/", v.d_customers, name="d_customers"),
]
