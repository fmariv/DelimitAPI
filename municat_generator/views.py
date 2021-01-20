# -*- coding: utf-8 -*-

# ----------------------------------------------------------
# TERRITORIAL DELIMITATION TOOLS (ICGC)
# Authors: Cesc Masdeu & Fran Martin
# Version: 0.1
# Date: 20210115
# Version Python: 3.7
# ----------------------------------------------------------

"""
Extract geometries and data from the database
"""

# Standard library imports
import os
import os.path as path
import shutil
import csv
from datetime import datetime
import logging

# Third party imports
import geopandas as gpd
from osgeo import gdal
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages

# Local imports
from municat_generator.config import *


class MunicatDataGenerator(View):
    """
    Class that extracts and manages geometries and data from the database with the main goal of creating a zip file
    package with them
    """
    # Workspace parameters
    current_date = datetime.now().strftime("%Y%m%d-%H%M")
    logger = logging.getLogger()
    # MTT parameters
    line_id = None
    session_id = None
    mtt_date = None
    mtt_num = None
    # Geodataframes for data managing
    line_tram_mem_gdf = None
    fita_mem_gdf = None
    line_id_muni_gdf = None
    line_tram_temp_gdf = None
    fita_temp_gdf = None
    # Municipis's names
    muni_1 = None
    muni_2 = None
    # Paths
    path_output_folder = None
    # Response data
    response_data = {}

    def get(self, request):
        """
        Main entry point. This method is called when someone wants to init the process of extracting and managing
        data from the database in order to create a package zip file that will be send to local governments.
        """
        # SET UP THE WORKING ENVIRONMENT -------------------------
        # Set up parameters
        self.set_up()
        # Set the layers geodataframe
        self.set_layers_gdf()

        # START THE PROCESS --------------------------------------
        # Check that the input data file exists
        if not path.exists(MTT):
            msg = "No s'ha trobat l'arxiu amb l'informació d'entrada"
            self.create_error_response(msg)

        with open(MTT) as f:
            f_reader = csv.reader(f, delimiter=",")
            for row in f_reader:
                # Read input data
                line_id = str(row[0])
                session_id = str(row[1])
                mtt_date = str(row[2])
                mtt_num = str(row[3])
                # Set those input data as class variables
                self.set_municat_data(line_id, session_id, mtt_date, mtt_num)
                # Get the names of the municipies
                self.get_muni_names()

                # Start extraction and data management
                try:
                    self.rm_temp()  # Delete previous temp files if exist
                except Exception as e:
                    msg = f'Error esborrant arxius temporals => {e}'
                    self.create_error_response(msg)
                # Check if the session_id exists in the database
                session_id_exists = self.check_session_id()
                if not session_id_exists:
                    msg = "L'ID Sessio introduït no existeix a la base de dades"
                    self.create_error_response(msg)
                # Extract points and lines and export them as shapefiles
                try:
                    self.extract_data()
                except Exception as e:
                    msg = f'Error extraient les geometries de la base de dades => {e}'
                    self.create_error_response(msg)
                # Check if exists other line ID's in the data extracted
                line_id_ok = self.check_line_id()
                if not line_id_ok:
                    msg = f'Hi ha un o més ID Linia a les dades que no corresponen a la linia {self.line_id}'
                    self.create_error_response(msg)
                # Delete auxiliary points from the point gdf
                self.delete_aux()
                # Delete and manage columns to the gdf
                self.manage_delete_fields()
                # Dissolve all the line trams into one single line
                self.dissolve_line()
                # Add columns with the names of the municipies to the gdf
                self.add_munis_names()
                # Check whether the points' geometry is valid
                self.check_points_geometry()
                # Export the data as ESRI shapefiles and DXF files
                self.export_data()
                # Copy PDF to the output folder
                self.copy_pdf()

                self.logger.info(f'Carpeta municat de la línia {line_id} generada correctament')
        # Send response as OK
        self.response_data['result'] = 'OK'
        self.response_data['message'] = f'Carpetes generades correctament'
        if self.response_data['result'] == 'OK':
            messages.success(request, 'Carpetes generades correctament!')
            return redirect("index")
        else:
            messages.warning(request, "No s'han generat les carpetes")
        return redirect("index")

    def set_up(self):
        """
        Set up the environment parameters that the class would need
        """
        # Configure logger
        self.set_logging_config()
        # Write first log message
        self.write_first_report()

    def set_logging_config(self):
        """
        Set up the logger config
        """
        # Logging level
        self.logger.setLevel(logging.INFO)
        # Message format
        log_format = logging.Formatter("%(levelname)s - %(message)s")
        # Log filename and path
        log_name = f"Municat_{self.current_date}.txt"
        log_path = os.path.join(LOG_DIR, log_name)
        file_handler = logging.FileHandler(filename=log_path, mode='w')
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)

    def set_layers_gdf(self):
        """Open all the necessary layers as geodataframes with geopandas"""
        # SIDM2
        self.line_tram_mem_gdf = gpd.read_file(WORK_GPKG, layer='tram_linia_mem')
        self.fita_mem_gdf = gpd.read_file(WORK_GPKG, layer='fita_mem')
        # Table id_linia_muni
        self.line_id_muni_gdf = gpd.read_file(WORK_GPKG, layer='id_linia_muni')

    def write_first_report(self):
        """Write first log's report"""
        init_log_report = f"Proces d'extraccio de dades pel Municat - {self.current_date}"
        self.logger.info(init_log_report)

    def set_municat_data(self, line_id, session_id, mtt_date, mtt_num):
        """

        :return:
        """
        self.line_id = line_id
        self.session_id = session_id
        self.mtt_date = mtt_date
        self.mtt_num = mtt_num

    def get_muni_names(self):
        """

        :return:
        """
        line_id_filter = self.line_id_muni_gdf['IDLINIA'] == int(self.line_id)
        munis_line_id = self.line_id_muni_gdf[line_id_filter]
        self.muni_1 = munis_line_id.NOMMUNI1.iloc[0].replace(' ', '_')
        self.muni_2 = munis_line_id.NOMMUNI2.iloc[0].replace(' ', '_')

    def check_session_id(self):
        """
        Check if the given session ID exists in the database, both in line and points layers
        :return:
        """
        if (self.session_id in self.line_tram_mem_gdf.id_sessio_.values) and (self.session_id in self.fita_mem_gdf.id_sessio_.values):
            return True
        else:
            return False

    def extract_data(self):
        """
        Extract, manage and export the data
        :return:
        """
        for layer in self.fita_mem_gdf, self.line_tram_mem_gdf:
            geom_type = ''
            session_line_id_gdf = layer[(layer['id_sessio_'] == self.session_id) & (layer['id_linia'] == float(self.line_id))]
            if layer.geom_type.iloc[0] == 'Point':
                geom_type = 'Fita'
            elif layer.geom_type.iloc[0] == 'MultiLineString':
                geom_type = 'Line_tram'
            # Check the result
            if geom_type != 'Fita' and geom_type != 'Line_tram':
                msg = 'Alguna de les geometries no són Punts o Multilínies'
                raise Exception(msg)
            # Export to the workspace geopackage
            layer_name = f'{geom_type}_mem_municat_temp'
            session_line_id_gdf.to_file(WORK_GPKG, layer=layer_name, driver="GPKG")
            # Set the new layers's geodataframes
            if geom_type == 'Fita':
                self.fita_temp_gdf = gpd.read_file(WORK_GPKG, layer=layer_name)
            elif geom_type == 'Line_tram':
                self.line_tram_temp_gdf = gpd.read_file(WORK_GPKG, layer=layer_name)

    def delete_aux(self):
        """

        :return:
        """
        # TODO comprovar amb una línia amb fites auxiliars
        self.fita_temp_gdf = self.fita_temp_gdf[self.fita_temp_gdf['id_u_fita'].str[-1] != '1']

    def manage_delete_fields(self):
        """

        :return:
        """
        # Points gdf
        point_delete_fields = ['id_fita', 'id_sessio_', 'num_sector', 'ini_sector', 'fin_sector', 'point_x', 'point_y',
                               'point_z', 'estat', 'num_fita_a', 'id_u_fita', 'etiqueta', 'id_punt', 'num_termes',
                               'trobada', 'auxiliar', 'observacio', 'metode', 'contacte', 'foto', 'mides',
                               'inscripcio', 'id_quadern', 'id_doc_act', 'tipus_doc_', 'data_doc', 'estat_sess',
                               'oficial', 'vigent']
        self.fita_temp_gdf = self.fita_temp_gdf.drop(columns=point_delete_fields)
        self.fita_temp_gdf = self.fita_temp_gdf.astype({'id_linia': int, 'num_fita': int})
        self.fita_temp_gdf = self.fita_temp_gdf.rename({'id_linia': 'ID_LINIA', 'num_fita': 'ID_FITA'}, axis='columns')

        # Lines gdf
        line_delete_fields = ['id_tram_li', 'id_sessio_', 'id_fita_1', 'id_fita_2', 'ordre', 'observacio', 'tipus_doc_',
                              'data_doc', 'estat_sess', 'oficial', 'vigent']
        self.line_tram_temp_gdf = self.line_tram_temp_gdf.drop(columns=line_delete_fields)
        self.line_tram_temp_gdf = self.line_tram_temp_gdf.astype({'id_linia': int})
        self.line_tram_temp_gdf = self.line_tram_temp_gdf.rename({'id_linia': 'ID_LINIA'}, axis='columns')

    def dissolve_line(self):
        """

        :return:
        """
        self.line_tram_temp_gdf = self.line_tram_temp_gdf.dissolve(by='ID_LINIA', as_index=False)

    def add_munis_names(self):
        """

        :return:
        """
        for layer in self.fita_temp_gdf, self.line_tram_temp_gdf:
            layer['NOMMUNI1'] = self.muni_1
            layer['NOMMUNI2'] = self.muni_2

    def check_points_geometry(self):
        """Check the points' geometry"""
        # Check if there are empty features
        is_empty = self.fita_temp_gdf.is_empty
        empty_features = self.fita_temp_gdf[is_empty]
        if not empty_features.empty:
            for index, feature in empty_features.iterrows():
                point_id = feature['ID_FITA']
                self.logger.error(f'      La fita {point_id} està buida')

        # Check if the geometry is valid
        is_valid = self.fita_temp_gdf.is_valid
        invalid_features = self.fita_temp_gdf[~is_valid]
        if not invalid_features.empty:
            for index, feature in invalid_features.iterrows():
                point_id = feature['ID_FITA']
                self.logger.error(f'      La fita {point_id} no té una geometria vàlida')

    def check_line_id(self):
        """

        :return:
        """
        # Points gdf
        not_line_id_fita = self.fita_temp_gdf['id_linia'] != int(self.line_id)
        not_line_id_fita_df = self.fita_temp_gdf[not_line_id_fita]
        if not not_line_id_fita_df.empty:
            return False

        # Lines gdf
        not_line_id_line = self.line_tram_temp_gdf['id_linia'] != int(self.line_id)
        not_line_id_line_df = self.line_tram_temp_gdf[not_line_id_line]
        if not not_line_id_line_df.empty:
            return False

        return True

    def export_data(self):
        """

        :return:
        """
        # Folders paths
        self.path_output_folder = os.path.join(FOLDERS, self.line_id)
        path_output_zip = os.path.join(self.path_output_folder, self.line_id)
        for path_ in self.path_output_folder, path_output_zip:
            if not path.exists(path_):
                os.mkdir(path_)

        # Line ID as txt
        line_id_txt = self.line_id_2_txt()

        # Layer names
        output_fita_lyr_name = f"MTT_F_{line_id_txt}_{self.mtt_date}_{self.mtt_num}_{self.muni_1}_{self.muni_2}"
        output_line_lyr_name = f"MTT_LT_{line_id_txt}_{self.mtt_date}_{self.mtt_num}_{self.muni_1}_{self.muni_2}"

        # Export data as shapefiles
        output_fita_shp = os.path.join(path_output_zip, f'{output_fita_lyr_name}.shp')
        output_line_shp = os.path.join(path_output_zip, f'{output_line_lyr_name}.shp')
        self.fita_temp_gdf.to_file(output_fita_shp)
        self.line_tram_temp_gdf.to_file(output_line_shp)

        # Export data as dxf files
        output_fita_dxf = os.path.join(path_output_zip, f'{output_fita_lyr_name}.dxf')
        output_line_dxf = os.path.join(path_output_zip, f'{output_line_lyr_name}.dxf')
        self.fita_temp_gdf.geometry.to_file(output_fita_dxf, driver='DXF')
        self.line_tram_temp_gdf.geometry.to_file(output_line_dxf, driver='DXF')

        # Create zip
        shutil.make_archive(path_output_zip, 'zip', path_output_zip)

        # Delete working folder
        shutil.rmtree(path_output_zip)

    def line_id_2_txt(self):
        """

        :return:
        """
        line_id_str = str(self.line_id)
        if len(line_id_str) == 1:
            line_id_txt = "000" + line_id_str
        elif len(line_id_str) == 2:
            line_id_txt = "00" + line_id_str
        elif len(line_id_str) == 3:
            line_id_txt = "0" + line_id_str
        else:
            line_id_txt = line_id_str

        return line_id_txt

    def copy_pdf(self):
        """

        :return:
        """
        line_dir = path.join(LINES_DIR, self.line_id)
        path_pdf_ed50 = path.join(line_dir, PDF_ED50)
        path_pdf_etrs89 = path.join(line_dir, PDF_ETRS89)
        path_pdf_output = path.join(self.path_output_folder, f'{self.line_id}.pdf')

        # Search the path where exists de PDF file
        path_pdf = ''
        pdf_start_filename = f"MTT_{self.line_id}_{self.mtt_date}_{self.mtt_num}_"
        for dirpath, dirnames, filenames in os.walk(path_pdf_etrs89):
            for filename in filenames:
                if filename.startswith(pdf_start_filename) \
                        and filename.endswith(".pdf"):
                    path_pdf = path.join(dirpath, filename)
        if not path_pdf:
            for dirpath, dirnames, filenames in os.walk(path_pdf_ed50):
                for filename in filenames:
                    if filename.startswith(pdf_start_filename) \
                            and filename.endswith(".pdf"):
                        path_pdf = path.join(dirpath, filename)
        if not path_pdf:
            self.logger.error("No s'ha trobat cap PDF a exportar")

        # Check whether the PDF file already exists into the output folder and remove it if exists
        if path.exists(path_pdf_output):
            os.remove(path_pdf_output)

        # Copy the PDF file into the output folder
        shutil.copyfile(path_pdf, path_pdf_output)

    def create_error_response(self, message):
        """Create a error JSON for the response data"""
        self.logger.error(message)
        self.response_data['result'] = 'error'
        self.response_data['message'] = message

    def rm_temp(self):
        """Remove temporal files from the workspace"""
        gpkg = gdal.OpenEx(WORK_GPKG, gdal.OF_UPDATE, allowed_drivers=['GPKG'])
        for layer in TEMP_ENTITIES:
            gpkg.ExecuteSQL(f'DROP TABLE {layer}')
        self.logger.info('Arxius temporals esborrats')
