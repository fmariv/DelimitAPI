from django.urls import path
from municat_generator.views import MunicatDataGenerator


urlpatterns = [
    path('', MunicatDataGenerator.as_view(), name='municat')
]
