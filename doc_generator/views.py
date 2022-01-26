# -*- coding: utf-8 -*-

# ----------------------------------------------------------
# TERRITORIAL DELIMITATION TOOLS (ICGC)
# Authors: Fran Martin
# Version: 1.0
# Version Python: 3.7
# ----------------------------------------------------------

# Standard library imports
import os
import csv
import math

# Third party imports
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
import pandas as pd
from mailmerge import MailMerge
from dotenv import load_dotenv

# Local imports
from doc_generator.config import *
from delimitapp.common.utils import line_id_2_txt

# Load dotenv in order to protect secret information
load_dotenv()

# TODO transformd word files into pdf files


class MunicatDataExtractor(View):
    """
    Class for generating the letters that the ICGC must send to the council in order to notify the begginig of a expedient
    """
    # Dataframes
    info_councils_df = pd.read_csv(INFO_MUNICAT_AJUNTAMENTS)
    info_line_id_df = pd.read_csv(INFO_MUNICAT_DATA)
    output_xls = None
    # Variables
    line_id = None
    url = None
    muni_1 = None
    muni_2 = None
    council_1_data = None
    council_2_data = None

    def get(self, request):
        """
        Main entry point. This method is called when someone wants to init the process of extracting the
        councils' data.
        """
        self.create_dataframe()  # Write CSV header

        duplicated_links = self.check_duplicated_links()  # Check if exists any duplicated link into the input data
        if duplicated_links:
            messages.error(request, "Existeixen links duplicats a l'arxiu CSV d'entrada de dades. Si us plau, revisa-ho")
            return redirect("letter-generator-page")

        for i, feature in self.info_line_id_df.iterrows():
            self.line_id = int(feature[0])
            self.url = feature[1]
            self.get_municipis_names()
            self.get_council_data()
            self.write_info_xls()
            self.reset_variables()

        messages.success(request, 'Informació del Municat extreta correctament')
        return redirect("letter-generator-page")

    def create_dataframe(self):
        """Funció per a escriure la capçalera al csv"""
        column_names = [
                "IDLINIA", "DATA-OD", "HORA-OD", "MUNI1", "LOCAL", "TRACTAMENT", "SEXE", "NOM1", "COGNOM1-1", "COGNOM1-2", "CARREC1", "NOMENS1",
                "MUNI2", "NOM2", "COGNOM2-1", "COGNOM2-2", "CARREC2", "NOMENS2", "LINK"
            ]
        self.output_xls = pd.DataFrame(columns=column_names)

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
        carrec_2 = muni_2_council_data.iloc[0]['CARREC'].split()[0]
        nomens_2 = muni_2_council_data.iloc[0]['NOMENS']

        if name_major_1 and name_major_2:   # Check that all the data is filled and wraps it
            self.council_1_data = pd.Series([self.line_id, '', '', self.muni_1, '', tractament_1, gender_1, name_major_1, surname_1_major_1,
                                            surname_2_major_1, carrec_1, nomens_1, self.muni_2, name_major_2, surname_1_major_2,
                                            surname_2_major_2, carrec_2, nomens_2, self.url], index=self.output_xls.columns)
            self.council_2_data = pd.Series([self.line_id, '', '', self.muni_2, '', tractament_2, gender_2, name_major_2, surname_1_major_2,
                                            surname_2_major_2, carrec_2, nomens_2, self.muni_1, name_major_1, surname_1_major_1,
                                            surname_2_major_1, carrec_1, nomens_1, self.url], index=self.output_xls.columns)

            for council_data in self.council_1_data, self.council_2_data:
                self.output_xls = self.output_xls.append(council_data, ignore_index=True)

    def write_info_xls(self):
        """
        Write the council's data into the output xls
        """
        self.output_xls.to_excel(INFO_MUNICAT_OUTPUT_DATA)

    def reset_variables(self):
        """
        Reset all the line variables and council's data to None
        """
        self.line_id = None
        self.url = None
        self.muni_1 = None
        self.muni_2 = None
        self.council_1_data = None
        self.council_2_data = None


def generate_letters_doc(request):
    """
    Generate all the letters in docx format
    :param request: Http request
    :return: redirect to the letter generator page
    """
    expedient = request.GET.get('expedient')
    info_municat_df = pd.read_excel(INFO_MUNICAT_OUTPUT_DATA)

    for i, feature in info_municat_df.iterrows():
        # Set doc variables depending on the expedient type
        short_line_id = feature['IDLINIA']
        line_id = line_id_2_txt(short_line_id)
        muni_1 = feature['MUNI1']
        tractament = feature['TRACTAMENT']
        sexe = feature['SEXE']
        nom = feature['NOM1']
        cognom_1 = feature['COGNOM1-1']
        cognom_2 = feature['COGNOM1-2']
        carrec = feature['CARREC1']
        nomens = feature['NOMENS1']
        salutacio = CASOS_SALUTACIO[sexe]
        muni_2 = feature['MUNI2']
        url = feature['LINK']
        if expedient == 'del':
            data_od_raw = feature['DATA-OD']
            hora_od = feature['HORA-OD']
            local = feature['LOCAL']
            if math.isnan(data_od_raw) or math.isnan(hora_od) or math.isnan(local):
                messages.error(request, f'Falta informació per indicar al csv info_municat')
                return redirect("letter-generator-page")
            muni_2_prep = feature['NOMENS2'].split('Ajuntament')[-1]
            data_od_splitted = data_od_raw.split('/')
            day = data_od_splitted[0]
            if day[0] == '0':
                day = day[1]
            data_od = f'{day} {MESOS_CAT[data_od_splitted[1]]} {data_od_splitted[2]}'
            if local == 'S':
                seu_od = 'del vostre ajuntament'
            elif local == 'N':
                seu_od = f"de l'ajuntament{muni_2_prep}"

        try:
            muni_2_prep, data_od, hora_od, seu_od, output_path, file_type = ('',) * 6
            if expedient == 'del':
                doc = MailMerge(TEMPLATE_DEL)
                output_path = AUTO_CARTA_OUTPUT_DOC_D
                file_type = 'CARTA_Inici_operacions_delimitacio'
                doc.merge(
                    Tractament=tractament,
                    Nom=nom,
                    Cognom1=cognom_1,
                    Cognom2=cognom_2,
                    Carrec=carrec,
                    nomens=nomens,
                    XXXX=line_id,
                    Salutacio=salutacio,
                    Prep_muni_visitant=muni_2_prep,
                    Data_od=data_od,
                    Hora_od=hora_od,
                    Seu_od=seu_od,
                    Link=url
                )
            elif expedient == 'rep':
                doc = MailMerge(TEMPLATE_REP)
                output_path = AUTO_CARTA_OUTPUT_DOC_R
                file_type = 'ofici_tramesa_replantejament'
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

            doc_output_path = os.path.join(output_path, f'{line_id}_{file_type}_{muni_1}.docx')
            doc.write(doc_output_path)
        except Exception as e:
            messages.error(request, f'Error generant les cartes en format docx: {e}')
            return redirect("letter-generator-page")
    messages.success(request, 'Cartes generades correctament en format docx')
    return redirect("letter-generator-page")


def remove_letters(request):
    """
    Remove all the files and letters generated in the output directories
    :param request: Http request
    :return: redirect to the letter generator page
    """
    output_directories_list = [AUTO_CARTA_OUTPUT_DOC_D, AUTO_CARTA_OUTPUT_PDF_D, AUTO_CARTA_OUTPUT_DOC_R,
                               AUTO_CARTA_OUTPUT_PDF_R]
    for output_directory in output_directories_list:
        for f in os.listdir(output_directory):
            file_ = os.path.join(output_directory, f)
            os.remove(file_)

    messages.success(request, 'Cartes eliminades correctament')
    return redirect("letter-generator-page")


def render_doc_generator_page(request):
    """
    Render the same doc generator page itself
    :param request: Http request
    :return: render -> Rendering of the doc generator page
    """
    return render(request, '../templates/doc_generator_page.html')


def render_letter_generator_page(request):
    """
    Render the letter generator page
    :param request: Http request
    :return: render -> Rendering of the letter generator page
    """
    return render(request, '../templates/letter_generator_page.html')
