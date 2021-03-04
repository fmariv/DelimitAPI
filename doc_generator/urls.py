from django.urls import re_path
from doc_generator.views import MunicatDataExtractor, render_doc_generator_page, render_letter_generator_page,\
    generate_letters_doc, generate_letters_pdf

'''
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
'''

urlpatterns = [
    re_path(r'^$', render_doc_generator_page, name='doc-generator-page'),
    re_path(r'^letters/$', render_letter_generator_page, name='letter-generator-page'),
    re_path(r'^letters/extract-municat/$', MunicatDataExtractor.as_view(), name='municat-data-extraction'),
    re_path(r'^letters/generate-doc/$', generate_letters_doc, name='doc-letter-generation'),
    re_path(r'^letters/generate-pdf/$', generate_letters_pdf, name='pdf-letter-generation'),

]
