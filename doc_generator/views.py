# -*- coding: utf-8 -*-

# ----------------------------------------------------------
# TERRITORIAL DELIMITATION TOOLS (ICGC)
# Authors: Fran Martin
# Version: 0.1
# Date: 20210224
# Version Python: 3.7
# ----------------------------------------------------------

# Standard library imports
import os
import os.path as path
from datetime import datetime
import logging
import csv
import urllib
import requests

# Third party imports
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
import pandas as pd
import comtypes.client
from mailmerge import MailMerge

# Local imports
from doc_generator.config import *


class LetterGenerator(View):
    """
    Class for generating the letters that the ICGC must send to the council in order to notify the begginig of a expedient
    # TODO split into 3 classes: extractor, generate doc and generate pdf
    """
    # DATA EXTRACTION ------------------------------------
    # Dataframes
    info_councils_df = pd.read_csv(INFO_MUNICAT_AJUNTAMENTS)
    info_line_id_df = pd.read_csv(INFO_MUNICAT_DATA)
    # Variables
    line_id = None
    shortened_url = None
    muni_1 = None
    muni_2 = None
    council_1_data = None
    council_2_data = None

    def get(self, request):
        """
        Main entry point. This method is called when someone wants to init the process of generating the
        councils' letters.
        """
        # EXTRACT THE DATA
        self.council_data_extraction()
        messages.success(request, 'OK')
        return redirect("doc-generator-page")

    def council_data_extraction(self):
        """Extract the given councils' data in order to properly generate the letters"""
        self.write_csv_head()   # Write CSV header
        duplicated_links = self.check_duplicated_links()   # Check if exists any duplicated link into the input data

        if duplicated_links:
            print('EXISTEIXEN LINKS DUPLICATS')
            return

        for i, feature in self.info_line_id_df.iterrows():
            self.line_id = int(feature[0])
            url = feature[1]
            self.get_municipis_names()
            self.shortened_url = self.short_url(url)
            self.get_council_data()
            self.write_info_csv()
            self.reset_variables()

    @staticmethod
    def write_csv_head():
        """Funció per a escriure la capçalera al csv"""
        with open(INFO_MUNICAT_OUTPUT_DATA, 'w', encoding='utf-8') as f:
            header = [
                "IDLINIA", "MUNI1", "TRACTAMENT", "SEXE", "NOM1", "COGNOM1-1", "COGNOM1-2", "CARREC1", "NOMENS1",
                "MUNI2", "NOM2", "COGNOM2-1", "COGNOM2-2", "CARREC2", "NOMENS2", "ENLLAÇ"
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

    def get_municipis_names(self):
        """
        Get the municipis that share a line
        """
        munis_line_id = INFO_MUNICAT_ID_LINIA[INFO_MUNICAT_ID_LINIA['IDLINIA'] == self.line_id]
        self.muni_1 = munis_line_id.NOMMUNI1.iloc[0]
        self.muni_2 = munis_line_id.NOMMUNI2.iloc[0]

    @staticmethod
    def short_url(long_url):
        """
        Short the given url in order to avoid problems by it length
        :param long_url: input data url
        :return: shortened url after short process
        """
        key = '8937dcbd67d56fcf61c45153173da9122e888'
        url = urllib.parse.quote(long_url)
        r = requests.get('http://cutt.ly/api/api.php?key={}&short={}'.format(key, url))

        if r.status_code == requests.codes.ok:
            response = r.json()
            shortened_url = response['url']['shortLink']
            return shortened_url
        else:
            print('Error escurçant link')
            # TODO
            pass

    def get_council_data(self):
        """
        Get the necessary council's data and wraps it
        """
        # First municipi's data
        muni_1_council_data = self.info_councils_df[self.info_councils_df['MUNICIPI'] == self.muni_1]
        tractament_1 = muni_1_council_data.iloc[0]['TRACTAMENT']
        gender_1 = muni_1_council_data.iloc[0]['SEXE']
        name_major_1 = muni_1_council_data.iloc[0]['NOM']
        surname_1_major_1 = muni_1_council_data.iloc[0]['COGNOM1']
        surname_2_major_1 = muni_1_council_data.iloc[0]['COGNOM2']
        carrec_1 = muni_1_council_data.iloc[0]['CARREC'].split()[0]   # .split() in order to obtain 'Alcalde' / 'Alcaldessa'
        nomens_1 = muni_1_council_data.iloc[0]['NOMENS']

        # Second municipi's data
        muni_2_council_data = self.info_councils_df[self.info_councils_df['MUNICIPI'] == self.muni_2]
        tractament_2 = muni_2_council_data.iloc[0]['TRACTAMENT']
        gender_2 = muni_2_council_data.iloc[0]['SEXE']
        name_major_2 = muni_2_council_data.iloc[0]['NOM']
        surname_1_major_2 = muni_2_council_data.iloc[0]['COGNOM1']
        surname_2_major_2 = muni_2_council_data.iloc[0]['COGNOM2']
        carrec_2 = muni_2_council_data.iloc[0]['CARREC'].split()[0]  # .split() in order to obtain 'Alcalde' / 'Alcaldessa'
        nomens_2 = muni_2_council_data.iloc[0]['NOMENS']

        if name_major_1 and name_major_2:   # Check that all the data is filled and wraps it
            self.council_1_data = [self.line_id, self.muni_1, tractament_1, gender_1, name_major_1, surname_1_major_1,
                                   surname_2_major_1, carrec_1, nomens_1, self.muni_2, name_major_2, surname_1_major_2,
                                   surname_2_major_2, carrec_2, nomens_2, self.shortened_url]
            self.council_2_data = [self.line_id, self.muni_2, tractament_2, gender_2, name_major_2, surname_1_major_2,
                                   surname_2_major_2, carrec_2, nomens_2, self.muni_1, name_major_1, surname_1_major_1,
                                   surname_2_major_1, carrec_1, nomens_1, self.shortened_url]

    def write_info_csv(self):
        """
        Write the council's data into the output csv
        """
        with open(INFO_MUNICAT_OUTPUT_DATA, 'a', encoding='utf-8') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(self.council_1_data)
            writer.writerow(self.council_2_data)

    def reset_variables(self):
        """
        Reset all the line variables and council's data to None
        """
        self.line_id = None
        self.shortened_url = None
        self.muni_1 = None
        self.muni_2 = None
        self.council_1_data = None
        self.council_2_data = None


def generate_letters_doc(self):
    """

    :return:
    """
    info_municat_df = pd.read_csv(INFO_MUNICAT_OUTPUT_DATA)
    doc = MailMerge(TEMPLATE)
    for i, feature in info_municat_df.iterrows():
        short_line_id = feature.iloc[0]['IDLINIA']
        line_id = self.line_id_2_txt(short_line_id)
        muni_1 = feature.iloc[0]['MUNI1']
        tractament = feature.iloc[0]['TRACTAMENT']
        sexe = feature.iloc[0]['SEXE']
        nom = feature.iloc[0]['NOM1']
        cognom_1 = feature.iloc[0]['COGNOM-1']
        cognom_2 = feature.iloc[0]['COGNOM-2']
        carrec = feature.iloc[0]['CARREC1']
        nomens = feature.iloc[0]['NOMENS1']
        salutacio = CASOS_SALUTACIO[sexe]
        muni_2 = feature.iloc[0]['MUNI2']
        url = feature.iloc[0]['ENLLAÇ']

        doc.merge(
            Tractament=tractament,
            Nom=nom,
            Cognom1=cognom_1,
            Cognom2=cognom_2,
            Carrec=carrec,
            nomens=nomens,
            XXXX=line_id,
            Salutacio=salutacio,
            Municipi2=muni_2,
            Link=url
        )

        doc_output_path = os.path.join(AUTO_CARTA_OUTPUT_DOC, f'{line_id}_ofici tramesa replantejament_{muni_1}.docx')
        doc.write(doc_output_path)


def generate_letters_pdf():
    """

    :return:
    """
    for f in os.listdir(AUTO_CARTA_OUTPUT_DOC):
        # Font -> https://stackoverflow.com/questions/6011115/doc-to-pdf-using-python
        in_file = os.path.join(AUTO_CARTA_OUTPUT_DOC, f)
        out_file = os.path.join(AUTO_CARTA_OUTPUT_DOC, f.replace("docx", "pdf"))

        wdFormatPDF = 17

        in_file = os.path.abspath(in_file)
        out_file = os.path.abspath(out_file)

        word = comtypes.client.CreateObject('Word.Application')
        doc = word.Documents.Open(in_file)
        doc.SaveAs(out_file, FileFormat=wdFormatPDF)
        doc.Close()
        word.Quit()


def line_id_2_txt(line_id):
    """
    Convert line id (integer) to string nnnn
    :return: line_id_txt -> <string> ID de la linia introduit en format text
    """
    line_id_str = str(line_id)
    if len(line_id_str) == 1:
        line_id_txt = "000" + line_id_str
    elif len(line_id_str) == 2:
        line_id_txt = "00" + line_id_str
    elif len(line_id_str) == 3:
        line_id_txt = "0" + line_id_str
    else:
        line_id_txt = line_id_str

    return line_id_txt


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
