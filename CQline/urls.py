from django.urls import path
from . import views

urlpatterns = [
    path('check-line', views.asview())
]

