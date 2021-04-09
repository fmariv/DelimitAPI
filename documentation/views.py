# Create your views here.
import os
from django.shortcuts import render, redirect
from dotenv import load_dotenv

# Load dotenv in order to protect secret information
load_dotenv()


def docs_home(request):
    return redirect(str(os.getenv('DOCS_URL')))


def docs_qa_line(request):
    return redirect(f"{str(os.getenv('DOCS_URL'))}qa_line/")


def docs_doc_generator(request):
    return redirect(f"{str(os.getenv('DOCS_URL'))}doc_generator/")

