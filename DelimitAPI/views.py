# Create your views here.
import os
from django.shortcuts import render, redirect
from dotenv import load_dotenv

# Load dotenv in order to protect secret information
load_dotenv()


def index(request):
    return render(request, '../../DelimitAPI/templates/index.html')


def documentation(request):
    return redirect(str(os.getenv('DOCS_URL')))
