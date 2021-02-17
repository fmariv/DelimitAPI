from django.urls import re_path
from doc_generator.views import LetterGenerator, render_doc_generator_page

'''
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
'''

urlpatterns = [
    re_path(r'^$', render_doc_generator_page, name='doc-generator-page'),
    re_path(r'^letters/$', LetterGenerator.as_view(), name='letter-generation')
]
