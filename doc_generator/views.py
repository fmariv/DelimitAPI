# -*- coding: utf-8 -*-

# ----------------------------------------------------------
# TERRITORIAL DELIMITATION TOOLS (ICGC)
# Authors: Fran Martin
# Version: 0.1
# Date: 20210217
# Version Python: 3.7
# ----------------------------------------------------------

# Standard library imports
import os
import os.path as path
from datetime import datetime
import logging
import csv

# Third party imports
import geopandas as gpd
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages

# Local imports
from doc_generator.config import *


class LetterGenerator(View):
    """
    Class for generating the letters that the ICGC must send to the council in order to notify the begginig of a expedient
    """

    def get(self, request):
        """
        Main entry point. This method is called when someone wants to init the process of generating the
        councils' letters.
        """
        # EXTRACT THE DATA
        self.council_data_extraction()

    def council_data_extraction(self):
        """Extract the given councils' data in order to properly generate the letters"""
        self.write_csv_head()   # Write CSV header
        duplicated_links = self.check_duplicated_links()   # Check if exists any duplicated link into the input data

        if duplicated_links:
            print('EXISTEIXEN LINKS DUPLICATS')
            return

        with open(INFO_MUNICAT_DATA, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                line_id = int(row[0])
                link = row[1]
                municipis = self.get_municipis_names(line_id)
                # self.short_link()
                # self.get_council_data()
                # self.write_info()

        # self.copy_csv()

    @staticmethod
    def write_csv_head():
        """Funció per a escriure la capçalera al csv"""
        with open(INFO_MUNICAT_OUTPUT_DATA, 'w', encoding='utf-8') as f:
            header = [
                "IDLINIA", "MUNI1", "TRACTAMENT", "SEXE", "NOM1", "COGNOM1-1", "COGNOM1-2", "CARREC1", "NOMENS1",
                "MUNI2",
                "NOM2", "COGNOM2-1", "COGNOM2-2", "CARREC2", "NOMENS2", "ENLLAÇ"
            ]
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(header)

    @staticmethod
    def check_duplicated_links():
        """
        Check wether exists duplicated links into the input data csv
        :return: boolean that indicates if exists any duplicated link
        """
        link_list = []
        duplicated = False

        with open(INFO_MUNICAT_DATA, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                link = row[1]
                link_list.append(link)

        for link in link_list:
            count = link_list.count(link)
            if count > 1:
                print("Link repetit -> " + link)
                duplicated = True

        return duplicated

    @staticmethod
    def get_municipis_names(line_id):
        """

        :param line_id:
        :return:
        """
        munis_line_id = INFO_MUNICAT_ID_LINIA[INFO_MUNICAT_ID_LINIA['IDLINIA'] == line_id]
        muni_1 = munis_line_id.NOMMUNI1.iloc[0]
        muni_2 = munis_line_id.NOMMUNI2.iloc[0]

        return [muni_1, muni_2]


class ResolutionGenerator(View):
    """
    Class for generating the DOGC's resolutions that have to publish in order ot notify the ending of a expedient
    """


def render_doc_generator_page(request):
    """
    Render the same doc generator page itself
    :param request: Rendering of the qa page
    :return:
    """
    return render(request, '../templates/doc_generator_page.html')
