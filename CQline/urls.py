from django.urls import path
from CQline.views import CheckQualityLine, open_qgis

'''
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
'''

urlpatterns = [
    path('check-line/<int:line_id>', CheckQualityLine.as_view()),
    path('check-line/open-qgis', open_qgis)
]
