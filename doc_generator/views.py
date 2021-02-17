# -*- coding: utf-8 -*-

# ----------------------------------------------------------
# TERRITORIAL DELIMITATION TOOLS (ICGC)
# Authors: Cesc Masdeu & Fran Martin
# Version: 0.1
# Date: 20210209
# Version Python: 3.7
# ----------------------------------------------------------

# Standard library imports
import os
import os.path as path
from datetime import datetime
import logging

# Third party imports
import geopandas as gpd
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages

# Local imports
from doc_generator.config import *


def render_doc_generator_page(request):
    """
    Render the same doc generator page itself
    :param request: Rendering of the qa page
    :return:
    """
    return render(request, '../templates/doc_generator_page.html')