# -*- coding: utf-8 -*-

# ----------------------------------------------------------
# TERRITORIAL DELIMITATION TOOLS (ICGC)
# Authors: Cesc Masdeu & Fran Martin
# Version: 0.1
# Date: 20210112
# Version Python: 3.7
# ----------------------------------------------------------

"""
Extract geometries and data from the database
"""

# Standard library imports
import os
import os.path as path
import shutil
import unicodedata
import csv
from datetime import datetime
import logging

# Third party imports
import geopandas as gpd
from osgeo import gdal
from django.http import JsonResponse
from django.views import View

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
    # Geodataframes for data managing
    line_tram_mem_gdf = None
    fita_mem_gdf = None
    line_id_muni_gdf = None
    line_tram_temp_gdf = None
    fita_temp_gdf = None

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

        # START THE PROCESS
        # Check that the input data file exists
        if not path.exists(MTT):
            self.logger.error("No existeix l'arxiu amb l'informació d'entrada")
            return

        with open(MTT) as f:
            f_reader = csv.reader(f, delimiter=",")
            for row in f_reader:
                # Read input data
                line_id = str(row[0])
                session_id = str(row[1])
                MTT_date = str(row[2])
                MTT_num = str(row[3])

                # Start extraction and data management
                try:
                    self.rm_temp()  # Delete previous temp files if exist
                except Exception as e:
                    self.logger.error(f'Error esborrant arxius temporals => {e}')
                    return

                # Check if the session_id exists in the database
                session_id_exists = self.check_session_id(session_id)
                if not session_id_exists:
                    self.logger.error("L'ID Sessio introduït no existeix a la base de dades.")
                    return
                # Extract points and lines and export them as shapefiles
                try:
                    self.extract_data(session_id, line_id)
                except Exception as e:
                    self.logger.error(f'Error esborrant arxius temporals => {e}')
                    return
                '''
                try:
                    delete_fields()
                except Exception:
                    print("Error eliminant camps de Fita_G")
                try:
                    dissolve_id_linia()
                except Exception:
                    print("Error al dissoldre Lin_Tram_Proposta")
                try:
                    add_fields()
                except Exception:
                    print("Error al afegir camps de nom de municipi")
                try:
                    add_nommuni_fitag()
                except Exception:
                    print("Error al afegir els noms de municipi a Fita_G")
                try:
                    add_nommuni_lin_tram()
                except Exception:
                    print("Error al afegir els noms de municipi a Lin_Tram_Proposta")
                try:
                    check_fc()
                except Exception:
                    print("Error al comprovar les FC")

                id_linia_checked = check_idlinia(id_linia_intro)

                if id_linia_checked:
                    print("Exportant zip i pdf...")
                    try:
                        export_objects(id_linia_intro, data_MTT_intro, num_MTT_intro)
                    except Exception:
                        print("Error al exportar les capes")
                    print("Esborrant arxius temporals...")
                    try:
                        borrar_temp(id_linia_intro)
                        print("******* Linia {0} exportada *******\n".format(id_linia_intro))
                    except Exception:
                        print("Error al esborrar els arxius temporals")
                else:
                    print("Hi ha mes idLinia repetits. Si us plau, revisa les capes")
                    borrar_temp(
                        id_linia_intro)  # S'eliminan els arxius temporals per a poder continuar el proces
                '''
        return JsonResponse({'message': 'done'})

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

    def check_session_id(self, session_id):
        """
        Check if the given session ID exists in the database, both in line and points layers
        :param session_id:
        :return:
        """
        if (session_id in self.line_tram_mem_gdf.id_sessio_.values) and (session_id in self.fita_mem_gdf.id_sessio_.values):
            return True
        else:
            return False

    def extract_data(self, session_id, line_id):
        """
        Extract and manage the point data
        :param session_id:
        :param line_id:
        :return:
        """

        for layer in self.fita_mem_gdf, self.line_tram_mem_gdf:
            session_line_id_gdf = layer[(layer['id_sessio_'] == session_id) & (layer['id_linia'] == float(line_id))]
            # Delete auxiliary points in point layer - last number in id_u_fita field == 1
            # TODO comprovar amb una línia amb fites auxiliars
            if layer.geom_type.iloc[0] == 'Point':
                session_line_id_gdf = session_line_id_gdf[session_line_id_gdf['id_u_fita'].str[-1] != '1']
                layer_name = 'Fita'
            else:
                layer_name = 'Line_tram'
            # Export to shapefile
            output_layer_path = os.path.join(OUTPUT, f'{layer_name}_mem_{line_id}_temp.shp')
            session_line_id_gdf.to_file(output_layer_path)
            # Set the new layers's geodataframes
            if layer_name == 'Fita':
                self.fita_temp_gdf = gpd.read_file(output_layer_path)
            elif layer_name == 'Line_tram':
                self.line_tram_temp_gdf = gpd.read_file(output_layer_path)

    def extract_line_trams(self, session_id, line_id):
        pass

    def rm_temp(self):
        """Remove temporal files from the workspace"""
        gpkg = gdal.OpenEx(WORK_GPKG, gdal.OF_UPDATE, allowed_drivers=['GPKG'])
        for layer in TEMP_ENTITIES:
            layer_name = layer.split('.')[0]
            gpkg.ExecuteSQL(f'DROP TABLE {layer_name}')

        self.logger.info('Arxius temporals esborrats')
