# Create your views here.
import os
from django.shortcuts import redirect
from dotenv import load_dotenv

# Load dotenv in order to protect secret information
load_dotenv()

DOCS_URL = str(os.getenv('DOCS_URL'))


def docs_home(request):
    return redirect(DOCS_URL)


def docs_qa_line(request):
    return redirect(f"{DOCS_URL}qa_line/")


def docs_doc_generator(request):
    return redirect(f"{DOCS_URL}doc_generator/")

