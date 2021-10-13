# -*- coding: utf-8 -*-

# ----------------------------------------------------------
# TERRITORIAL DELIMITATION TOOLS (ICGC)
# Authors: Cesc Masdeu & Fran Martin
# Version: 1.2
# Version Python: 3.7
# ----------------------------------------------------------

"""
Quality check of a line ready to upload to the database
"""

import os
import os.path as path
from datetime import datetime
import logging
import re
import shutil

import geopandas as gpd
import fiona
from osgeo import gdal
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages

from qa_line.config import *
from delimitapp.common.utils import line_id_2_txt


class CheckQualityLine(View):
    """
    Class for checking a line's geometry and attributes quality previously to upload it into the database
    """
    # Workspace parameters
    line_id = None
    line_type = None
    line_id_txt = None
    current_date = None
    logger = logging.getLogger()
    log_path = None
    ppf_list = None
    fites_list = None
    found_points_dict = None
    # Paths to directories and folders
    line_folder = None
    doc_delim = None
    carto_folder = None
    tables_folder = None
    photo_folder = None
    # Geodataframes and layers for data managing
    tram_line_mem_gdf = None
    fita_mem_gdf = None
    tram_line_rep_gdf = None
    fita_rep_gdf = None
    lin_tram_ppta_line_gdf = None
    lin_tram_line_gdf = None
    punt_line_gdf = None
    tram_line_layer = None
    db_line_layer = None
    db_point_layer = None
    p_proposta_df = None
    punt_fit_df = None
    # Coordinates data structures
    points_coords_dict = None
    line_coords_list = None
    # Json response
    response_data = {}

    def get(self, request):
        """
        Main entry point. Here is where the magic is done. This method is called when someone wants to init the process of quality
        checking and is supposed to prepare the workspace, prepare the line and check it's geometry and attributes
        """
        # #######################
        # SET UP THE WORKING ENVIRONMENT
        # Set up parameters
        line_id = request.GET.get('line_id')
        line_type = request.GET.get('line_type')
        # Check the line ID input
        if not line_id:
            messages.error(request, "No s'ha introduit cap ID Linia")
            return redirect("qa-page")
        if int(line_id) < 0:
            messages.error(request, "L'ID Linia no es vàlid")
            return redirect("qa-page")
        # Check that the upload line directory exists
        line_dir_exists = self.check_line_dir_exists(line_id)
        if not line_dir_exists:
            messages.error(request, f"No existeix la carpeta de la linia {line_id} al directori de càrrega.")
            return redirect("qa-page")
        # Set up environment variables
        self.set_up(line_id, line_type)
        # Check and set directories paths
        # From this step to above the bugs and reports are going to be written into the log report
        self.logger.info("Validant i preparant l'entorn de treball...")
        directory_tree_valid = self.check_directories()
        if directory_tree_valid:
            self.set_directories()
        else:
            msg = "L'estructura de directoris de la carpeta de la linia no és vàlida. Si us plau, revisa" \
                  " que la carpeta DocDelim existeixi i que tots els seus subdirectoris també."
            response = self.create_error_response(msg)
            return render(request, '../templates/qa_reports.html', response)
        # Remove temp files from the workspace
        try:
            self.rm_temp()
        except Exception as e:
            msg = f'Error esborrant arxius temporals => {e}'
            response = self.create_error_response(msg)
            return render(request, '../templates/qa_reports.html', response)
        # Check if all the necessary entities exist
        entities_exist = self.check_entities_exist()
        if not entities_exist:
            msg = "Falten capes o taules necessaries pel procés de control de qualitat. Si us plau, revisa que totes les capes i taules" \
                  " estiguin a les carpetes 'Cartografia' i 'Taules'."
            response = self.create_error_response(msg)
            return render(request, '../templates/qa_reports.html', response)
        # Copy layers and tables from line's folder to the workspace
        copied_data_ok = self.copy_data_2_gpkg()
        if not copied_data_ok:
            msg = "No s'han pogut copiar capes o taules. Veure log per més informació."
            response = self.create_error_response(msg)
            return render(request, '../templates/qa_reports.html', response)
        # Set the layers geodataframes
        self.set_layers_gdf()
        # Create list with only points that are "Proposta Final"
        if self.line_type == 'mtt': self.ppf_list = self.get_ppf_list()
        # Create list with only points that are "Fita"
        self.fites_list = self.get_fites_list()
        # Create dict with the only points that are found, and PPF if the line is official
        self.found_points_dict = self.get_found_points_dict()
        # Get a dict with the points ID and their coordinates
        self.points_coords_dict = self.get_point_coordinates()
        # Get a list with the line coordinates
        self.line_coords_list = self.get_line_coordinates()

        # #######################
        # DATA CHECKING
        # Check if the line ID already exists into the database
        self.check_line_id_exists()
        # Check if the line's field structure and content is correct
        tram_line_ok = self.check_tram_line_layer()
        if not tram_line_ok:
            msg = "L'estructura de camps de la capa de trams de línia no és correcte i no es pot continuar el procés," \
                  " donat que hi ha algun camp que falta o sobra a la capa. Si us plau, revisa-la."
            response = self.create_error_response(msg)
            return render(request, '../templates/qa_reports.html', response)
        # Check the line and point's geometry
        self.check_layers_geometry()
        # Check that all the points indicated in the line layer exists in the tables and have filled correctly
        # all the attributes
        self.check_lin_tram_points()
        # Get info from the parts and vertex of every line tram
        self.info_vertex_line()
        # Check some aspects about found points, first of all checking if exists any found point
        if self.found_points_dict: self.check_found_points()
        # Check if the 3T points are indicated correctly
        self.check_3termes()
        # Check some aspects about the decimals and the PPF points, only if the line is official
        if self.line_type == 'mtt':
            # Check that the points are correctly rounded
            self.check_points_decimals()
            # Get info and check the features in P_Proposta
            self.info_p_proposta()
        # Check the relation between the tables and the point layer
        self.check_relation_points_tables()
        # Check the topology in order to avoid topological errors
        self.check_topology()

        # #######################
        # RESPONSE SEND
        # Remove working directory
        self.rm_working_directory()
        # Send response as OK
        self.response_data['result'] = 'OK'
        self.response_data['message'] = f'Linia {line_id} validada'
        response = self.add_response_data()
        request.session['response'] = response
        self.reset_logger()  # Reset the logger to avoid modify tbe later reports done
        return redirect('qa-report')

    def set_up(self, line_id, line_type):
        """
        Set up the environment parameters that the class would need
        :param line_id: line ID from the line the class is going to check
        :param line_type: line type from the line the class is going to check. It can be 'mtt' or 'rep', and
                          means whether the line is official or not
        """
        # Set line ID
        self.line_id = line_id
        # Set line type
        self.line_type = line_type
        # Convert line ID from integer to string nnnn
        self.line_id_txt = line_id_2_txt(self.line_id)
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
        log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        # Log filename and path
        self.current_date = datetime.now().strftime("%Y%m%d-%H%M")
        log_name = f"QA_log-{self.line_id_txt}-{self.current_date}.txt"
        log_dir = WORK_REC_DIR if self.line_type == 'mtt' else WORK_REP_DIR
        self.log_path = path.join(LINES_DIR, self.line_id, log_dir, log_name)
        if path.exists(self.log_path):  # If a log with the same filename exists, removes it
            os.remove(self.log_path)
        file_handler = logging.FileHandler(filename=self.log_path, mode='a')
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)

    def check_line_dir_exists(self, line_id):
        """
        Check if the line folder exists in the uploading directory and copy it into the working directory
        :return: boolean that indicates whether the line folder exists or not
        """
        line_folder = os.path.join(UPLOAD_DIR, str(line_id))
        if path.exists(line_folder):
            local_line_folder = os.path.join(WORK_DIR, str(line_id))
            if os.path.exists(local_line_folder):
                shutil.rmtree(local_line_folder)
            shutil.copytree(line_folder, local_line_folder)
            self.line_folder = local_line_folder
            return True
        else:
            return False

    def check_directories(self):
        """
        Check if the directory tree structure and content is correct
        :return: boolean that indicates if the line's folder's directory tree is correct or not
        """
        tree_valid = True

        doc_delim = os.path.join(self.line_folder, 'DocDelim')
        if path.exists(doc_delim):  # Check the DocDelim folder exists
            self.doc_delim = doc_delim
            for sub_dir in SUB_DIR_LIST:  # Check if all the subdirs exist
                if sub_dir not in os.listdir(self.doc_delim):
                    tree_valid = False
                    self.logger.critical(f'   No existeix el subdirectori {sub_dir}')
        else:
            self.logger.critical('   No existeix DocDelim dins el directori de la linia')
            tree_valid = False

        if tree_valid:
            self.logger.info('   Estructura de directoris OK')
            return tree_valid

    def set_directories(self):
        """Set paths to directories"""

        self.carto_folder = os.path.join(self.doc_delim, 'Cartografia')
        self.tables_folder = os.path.join(self.doc_delim, 'Taules')
        self.photo_folder = os.path.join(self.doc_delim, 'Fotografies')

    def set_layers_gdf(self):
        """Open all the necessary layers as geodataframes with geopandas"""
        # Lines and points
        if self.line_type == 'mtt':
            # DB layers
            self.tram_line_mem_gdf = gpd.read_file(WORK_GPKG, layer='tram_linia_mem')
            self.fita_mem_gdf = gpd.read_file(WORK_GPKG, layer='fita_mem')
            # Line layer
            self.lin_tram_ppta_line_gdf = gpd.read_file(WORK_GPKG, layer='Lin_TramPpta')
            # Tables
            self.p_proposta_df = gpd.read_file(WORK_GPKG, layer='P_Proposta')
        elif self.line_type == 'rep':
            # DB layers
            self.tram_line_rep_gdf = gpd.read_file(WORK_GPKG, layer='tram_linia_rep')
            self.fita_rep_gdf = gpd.read_file(WORK_GPKG, layer='fita_rep')
            # Line layer
            self.lin_tram_line_gdf = gpd.read_file(WORK_GPKG, layer='Lin_Tram')
            # Tables
            if 'P_Proposta' in fiona.listlayers(WORK_GPKG):   # P_Proposta table can be empty if the line type is a replantejament
                self.p_proposta_df = gpd.read_file(WORK_GPKG, layer='P_Proposta')
        self.punt_line_gdf = gpd.read_file(WORK_GPKG, layer='Punt')
        self.punt_fit_df = gpd.read_file(WORK_GPKG, layer='PUNT_FIT')

        # Set common line type layer. Depending on the function logic it has to take the official line layer or
        # the non official line layer. In order to don't repeat the layer variable declaration, it is declared here
        if self.line_type == 'mtt':
            # Line layer
            self.tram_line_layer = self.lin_tram_ppta_line_gdf
            # Database layers
            self.db_line_layer = self.tram_line_mem_gdf
            self.db_point_layer = self.fita_mem_gdf
        elif self.line_type == 'rep':
            self.db_line_layer = self.tram_line_rep_gdf
            self.db_point_layer = self.fita_rep_gdf
            self.tram_line_layer = self.lin_tram_line_gdf

    def check_entities_exist(self):
        """
        Check if all the necessary shapefiles and tables exists
        :return: entities_exist - Boolean that means if all the entities exists in the source workspace
        """
        shapes_exist, tables_exist = False, False
        for shape in SHAPES_LIST:
            shape_path = os.path.join(self.carto_folder, shape)
            if path.exists(shape_path):
                shapes_exist = True
            else:
                shapes_exist = False

        for dbf in TABLE_LIST:
            dbf_path = os.path.join(self.tables_folder, dbf)
            if path.exists(dbf_path):
                tables_exist = True
            else:
                tables_exist = False

        if not shapes_exist and not tables_exist:
            self.logger.critical('   Falten capes i taules necessàries a les carpetes de Cartografia i Taules')
            return False
        elif not shapes_exist and tables_exist:
            self.logger.critical('   Falten capes necessàries a la carpeta de Cartografia')
            return False
        elif shapes_exist and not tables_exist:
            self.logger.critical('   Falten taules necessàries a la carpeta de Taules')
            return False
        else:
            return True

    def copy_data_2_gpkg(self):
        """Copy all the feature classes and tables from the line's folder to the local work geopackage"""
        shapes_list = OFFICIAL_SHAPES_LIST if self.line_type == 'mtt' else NONOFFICIAL_SHAPES_LIST
        for shape in shapes_list:
            shape_name = shape.split('.')[0]
            shape_path = os.path.join(self.carto_folder, shape)
            try:
                shape_gdf = gpd.read_file(shape_path)
                shape_gdf.to_file(WORK_GPKG, layer=shape_name, driver="GPKG")
            except Exception as e:
                self.logger.critical(f"   No s'ha pogut copiar la capa {shape_name} => {e}")
                return False

        for dbf in TABLE_LIST:
            dbf_name = dbf.split('.')[0]
            dbf_path = os.path.join(self.tables_folder, dbf)
            try:
                dbf_gdf = gpd.read_file(dbf_path)
                if self.line_type == 'rep' and dbf_name == 'P_Proposta':   # P_Proposta table can be empty if the line type is a replantejament
                    if not dbf_gdf.empty:
                        dbf_gdf.to_file(WORK_GPKG, layer=dbf_name, driver="GPKG")
                else:
                    dbf_gdf.to_file(WORK_GPKG, layer=dbf_name, driver="GPKG")
            except Exception as e:
                self.logger.error(f"   No s'ha pogut copiar la taula {dbf_name} => {e}")
                return False

        self.logger.info(f"   Capes i taules de la linia {self.line_id} copiades correctament al geopackage local")
        return True

    def check_line_id_exists(self):
        """Check if the line ID already exists into the database, both into fita_mem and lin_tram_mem"""
        self.logger.info("Comprovant l'existencia de la linia a la base de dades...")
        line_id_in_lin_tram, line_id_in_fita_g = False, False
        line_type = 'mem' if self.line_type == 'mtt' else 'rep'

        # Check in lin_tram layer
        tram_duplicated_id = self.db_line_layer['id_linia'] == int(self.line_id)
        tram_line_id = self.db_line_layer[tram_duplicated_id]
        if not tram_line_id.empty:
            line_id_in_lin_tram = True

        # Check in fita layer
        fita_duplicated_id = self.db_point_layer['id_linia'] == int(self.line_id)
        fita_line_id = self.db_point_layer[fita_duplicated_id]
        if not fita_line_id.empty:
            line_id_in_fita_g = True

        if line_id_in_fita_g and line_id_in_lin_tram:
            self.logger.error(f"   L'ID de linia introduit esta en fita_{line_type} i tram_linia_{line_type}")
        elif line_id_in_fita_g and not line_id_in_lin_tram:
            self.logger.error(f"   L'ID de linia introduit esta en fita_{line_type} pero no en lin_tram_{line_type}")
        elif not line_id_in_fita_g and line_id_in_lin_tram:
            self.logger.error(f"   L'ID de linia introduit no esta en fita_{line_type} pero si en lin_tram_{line_type}")
        elif not line_id_in_fita_g and not line_id_in_lin_tram:
            self.logger.info(f"   L'ID de linia no esta repetit a fita_{line_type} ni a lin_tram_{line_type} de SIDM3")

    def check_tram_line_layer(self):
        """Check line's layer's field structure and content"""
        # The line's layer's field structure is critic for the correct running of the QA process. If it's not correct,
        # the process must stop
        self.logger.info("Validant l'estructura de camps i contingut de la capa de trams...")
        fields_lin_tram_ok = self.check_fields_tram_line_layer()
        if not fields_lin_tram_ok:
            return False
        if self.line_type == 'mtt':
            self.check_fields_content_lint_tram_ppta()

        return True

    def check_fields_tram_line_layer(self):
        """Check line's layer's field structure is correct"""
        lin_tram_fields, true_fields, layer = None, None, ''

        if self.line_type == 'mtt':
            # Fields that the line's layer must have
            true_fields = ('ID_LINIA', 'ID', 'DATA', 'COMENTARI', 'P1', 'P2', 'P3', 'P4', 'PF',
                           'ID_FITA1', 'ID_FITA2', 'geometry')
            lin_tram_fields = list(self.lin_tram_ppta_line_gdf.columns)
            layer = 'Lin Tram Proposta'
        elif self.line_type == 'rep':
            true_fields = ('ID', 'ID_LINIA', 'ID_SECTOR', 'ID_TRAM', 'OBSERVACIO', 'CORR_DIF', 'ID_FITA1', 'ID_FITA2',
                           'geometry')
            lin_tram_fields = list(self.lin_tram_line_gdf.columns)
            layer = 'Lin Tram'

        # Compare
        field_match = 0
        for field in lin_tram_fields:
            if field in true_fields:
                field_match += 1
        if field_match == len(true_fields):
            self.logger.info(f"   L'estructura de camps de {layer} es correcte")
            return True
        else:
            self.logger.critical(f"   L'estructura de camps de {layer} NO es correcte")
            return False

    def check_fields_content_lint_tram_ppta(self):
        """Check line's layer's content is correct"""
        # Check that doesn't exist the line ID from another line
        line_id_error = False
        not_line_id = self.lin_tram_ppta_line_gdf['ID_LINIA'] != int(self.line_id)
        tram_not_line_id = self.lin_tram_ppta_line_gdf[not_line_id]
        if not tram_not_line_id.empty:
            line_id_error = True
            self.logger.error("   Existeixen trams de linia amb l'ID d'una altra linia")

        # Check that the fita ID is correct
        id_fita_error = False
        # F1
        id_f1_bad = self.lin_tram_ppta_line_gdf['ID_FITA1'] == '1'
        tram_id_f1_bad = self.lin_tram_ppta_line_gdf[id_f1_bad]
        # F2
        id_f2_bad = self.lin_tram_ppta_line_gdf['ID_FITA2'] == '1'
        tram_id_f2_bad = self.lin_tram_ppta_line_gdf[id_f2_bad]

        if not tram_id_f1_bad.empty or not tram_id_f2_bad.empty:
            id_fita_error = True
            self.logger.error("   El camp ID FITA d'algun dels trams de la linia no és valid")

        if not line_id_error and not id_fita_error:
            self.logger.info("   Els camps de Lin Tram Proposta estan correctament emplenats")

    def get_ppf_list(self):
        """
        Get dataframe with the ID of the only points that are "Punt Proposta Final", as known as "PPF"
        :return: ppf_list - List with the ID of the PPF
        """
        is_ppf = self.p_proposta_df['PFF'] == 1
        ppf_df = self.p_proposta_df[is_ppf]
        ppf_list = ppf_df['ID_PUNT'].to_list()

        return ppf_list

    def get_fites_list(self):
        """
        Get dataframe with the ID of the only points that are "fites".
        :return: fites_list - List with the ID of the fites
        """
        fites = self.punt_fit_df['ID_PUNT'].to_list()

        return fites

    def get_found_points_dict(self):
        """
        Get a dict of the found points with etiqueta as key and ID_PUNT as value. If the line is official, the dict
        only contains the PPF found points. If not, it returns all the found points.
        :return: points_found_dict - Dict of the found points with the key, value -> ID_FITA, ID_Punt
        """
        points_found_dict = {}
        found = self.punt_fit_df['TROBADA'] == '1'
        points_found = self.punt_fit_df[found]
        if not points_found.empty:
            for index, feature in points_found.iterrows():
                if self.line_type == 'mtt':
                    if feature['ID_PUNT'] in self.ppf_list:
                        if feature['AUX'] == '1':
                            point_num = f"{feature['ID_FITA']}-aux"
                        else:
                            point_num = feature['ID_FITA']
                        point_id = feature['ID_PUNT']
                        points_found_dict[point_num] = point_id
                elif self.line_type == 'rep':
                    if feature['AUX'] == '1':
                        point_num = f"{feature['ID_FITA']}-aux"
                    else:
                        point_num = feature['ID_FITA']
                    point_id = feature['ID_PUNT']
                    points_found_dict[point_num] = point_id

            return points_found_dict

        else:
            return False

    def check_layers_geometry(self):
        """ Check the geometry of both line and points """
        line_layer = 'Lin Tram Proposta' if self.line_type == 'mtt' else 'Lin Tram'
        self.logger.info('Validant geometries...')
        self.logger.info(f'   {line_layer}:')
        self.check_lin_tram_geometry()
        self.logger.info('   Punt:')
        self.check_points_geometry()

    def check_lin_tram_points(self):
        """
        Check that the points indicated into the line layer as initial and final point exist in the
        tables and have all them attributes correctly filled
        :return: boolean - Indicates whether the points exist in the tables or not
        """
        lin_tram_point_1 = self.tram_line_layer['ID_FITA1'].to_list()
        lin_tram_point_2 = self.tram_line_layer['ID_FITA2'].to_list()
        lin_tram_points = lin_tram_point_1 + lin_tram_point_2
        lin_tram_points = list(set(lin_tram_points))
        none_exists = any(x is None for x in lin_tram_points)
        if none_exists:
            self.logger.error("   Atencio: hi ha trams on falta alguna fita per indicar. Revisa si es un error o no es un tram que arriva al mar")

        if self.line_type == 'mtt':
            points_in_ppf = True
            for point in lin_tram_points:
                if point is not None:
                    if point not in self.ppf_list and points_in_ppf:
                        point_id = point.split('-')[-1]
                        self.logger.error(
                            f"   La fita amb ID PUNT: {point_id} esta indicada com a fita inicial o final d'un tram "
                            f"pero no esta indicada com a Punt Proposta Final")

        points_in_fites = True
        for point_ in lin_tram_points:
            if point_ is not None:
                if point_ not in self.fites_list and points_in_fites:
                    point_id_ = point_.split('-')[-1]
                    self.logger.error(
                        f"   La fita amb ID PUNT: {point_id_} esta indicada com a fita inicial o final d'un tram "
                        f"pero no esta indicada com a fita")

    def check_lin_tram_geometry(self):
        """ Check the line's geometry """
        # Set line type layer
        layer = 'Lin Tram Proposta' if self.line_type == 'mtt' else 'Lin Tram'

        # Check if there are empty features
        is_empty = self.tram_line_layer.is_empty
        empty_features = self.tram_line_layer[is_empty]
        if not empty_features.empty:
            for index, feature in empty_features.iterrows():
                tram_id = feature['ID']
                self.logger.error(f'      El tram {tram_id} esta buit')
        # Check if there is a ring
        is_ring = self.tram_line_layer.is_empty
        ring_features = self.tram_line_layer[is_ring]
        if not ring_features.empty:
            for index, feature in ring_features.iterrows():
                tram_id = feature['ID']
                self.logger.error(f'      El tram {tram_id} te un anell interior')
        # Check if the line is multi-part and count the parts in that case
        not_multipart = True
        for index, feature in self.tram_line_layer.iterrows():
            geom_type = feature['geometry'].geom_type
            if geom_type == 'MultiLineString':
                not_multipart = False
                tram_id = feature['ID']
                n_parts = feature['geometry'].geoms
                self.logger.error(f'      El tram {tram_id} es multi-part i te {n_parts} parts')

        if empty_features.empty and ring_features.empty and not_multipart:
            self.logger.info(f"      No s'ha detectat cap error de geometria a {layer}")

    def check_points_geometry(self):
        """Check the points' geometry"""
        # Check if there are empty features
        is_empty = self.punt_line_gdf.is_empty
        empty_features = self.punt_line_gdf[is_empty]
        if not empty_features.empty:
            for index, feature in empty_features.iterrows():
                point_id = feature['ID_PUNT']
                self.logger.error(f'      El punt {point_id} esta buit')
        # Check if the geometry is valid
        is_valid = self.punt_line_gdf.is_valid
        invalid_features = self.punt_line_gdf[~is_valid]
        if not invalid_features.empty:
            for index, feature in invalid_features.iterrows():
                point_id = feature['ID_PUNT']
                self.logger.error(f'      El punt {point_id} no te una geometria valida')

        if empty_features.empty and invalid_features.empty:
            self.logger.info("      No s'ha detectat cap error de geometria a la capa Punt")

    def info_vertex_line(self):
        """Get info and make a recount of the line's vertexs"""
        self.logger.info('Obtenint relacio de vertex per tram de linia...')
        # TODO sort by tram ID
        for index, feature in self.tram_line_layer.iterrows():
            tram_id = feature['ID']
            tram_vertexs = len(feature['geometry'].coords)  # Nº of vertexs that compose the tram
            self.logger.info(f"   Tram ID: {tram_id}   Nº vertex: {tram_vertexs}")

    def check_points_decimals(self):
        """Check if the points's decimals are correct and are rounded to 1 decimal"""
        decim_valid = True
        for index, feature in self.punt_line_gdf.iterrows():
            # Point parameters
            '''
            Due the add respone function converts all the logger's messages into a JSON splitting the reports by "-"
            is mandatory to avoid using that character in the reports in order to don't lose data adding the messages
            to the JSON.
            '''
            if feature['ID_PUNT'] in self.ppf_list:  # Check if the point is a ppf point
                point_num = feature['ETIQUETA'].split('-')[-1]
                point_id = feature['ID_PUNT'].split('-')[-1]
                point_x = feature['geometry'].x
                point_y = feature['geometry'].y
                # Check if rounded correctly
                dif_x = abs(point_x - round(point_x, 1))
                dif_y = abs(point_y - round(point_y, 1))
                if dif_x > 0.01 or dif_y > 0.01:
                    decim_valid = False
                    self.logger.error(
                        f"   La fita {point_num} amb ID_PUNT {point_id} no esta correctament decimetritzada")

        if decim_valid:
            self.logger.info('   Les fites estan correctament decimetritzades')

    def info_p_proposta(self):
        """
        Get info and check the points in the table P_Proposta, like:
            - Count the points and distinguish them depending on its type
            - Check that the field ORDPF is not NULL
            - Check that an auxiliary point is not indicated as a real point
        """
        self.logger.info('Obtenint informacio de les fites proposta...')
        # Count the points in the table P_Proposta depending on the point's type
        self.count_points()
        # Check that ORDPF is not null
        ordpf_valid = self.check_ordpf()
        # Check that the points in P_Proposta are correctly indicated
        real_points_valid = self.check_real_points()
        if ordpf_valid and real_points_valid:
            self.logger.info(f'   Tots els registre de la taula P Proposta son valids')

    def count_points(self):
        """Count the points in the table P_Proposta and distinguish them depending on its type"""
        # Not final points
        # PFF = 0
        not_ppf = self.p_proposta_df['PFF'] == 0
        not_final_points = self.p_proposta_df[not_ppf]
        n_not_final_points = not_final_points.shape[0]
        # Real points
        # PFF = 1 AND ESFITA = 1
        proposta_points = self.p_proposta_df.loc[(self.p_proposta_df['PFF'] == 1) & (self.p_proposta_df['ESFITA'] == 1)]
        n_proposta_points = proposta_points.shape[0]
        # Auxiliary points
        # PFF = 1 AND ESFITA = 0
        auxiliary_points = self.p_proposta_df.loc[
            (self.p_proposta_df['PFF'] == 1) & (self.p_proposta_df['ESFITA'] == 0)]
        n_auxiliary_points = auxiliary_points.shape[0]

        self.logger.info(f'   Fites PPF reals: {n_proposta_points}')
        self.logger.info(f'   Fites PPF auxiliars: {n_auxiliary_points}')
        self.logger.info(f'   Fites no finals: {n_not_final_points}')

    def check_ordpf(self):
        """
        Check the field ORDPF is not NULL
        :return valid - Boolean that means if the ORDPF field is OK
        """
        valid = True
        ordpf_null = self.p_proposta_df['ORDPF'].isnull()
        points_ordpf_null = self.p_proposta_df[ordpf_null]

        if not points_ordpf_null.empty:
            valid = False
            for index, feature in points_ordpf_null.iterrows():
                point_id = feature['ID_PUNT'].split('-')[-1]
                self.logger.error(f"   El camp ORDPF del punt {point_id} a la taula P_PROPOSTA es nul")

        return valid

    def check_real_points(self):
        """Check that an auxiliary point is not indicated as a real point"""
        # If PPF = 1 and ORDPF = 0 => ESFITA MUST BE 0
        valid = True
        bad_auxiliary_points = self.p_proposta_df.loc[(self.p_proposta_df['PFF'] == 1) &
                                                      (self.p_proposta_df['ORDPF'] == 0) &
                                                      (self.p_proposta_df['ESFITA'] != 0)]

        if not bad_auxiliary_points.empty:
            valid = False
            for index, feature in bad_auxiliary_points.iterrows():
                point_id = feature['ID_PUNT'].split('-')[-1]
                self.logger.error(
                    f"   El punt amb ID PUNT : {point_id} està mal indicat a P_Proposta: sembla que es tracta "
                    f"d'una fita auxiliar indicada com a fita real.")

        return valid

    def check_found_points(self):
        """
        Check diferent things about the found points, like:
            - Has photography
            - The photography exists in its folder
            - If the point has Z coordinate must be found point
        """
        self.logger.info("Validant el contingut de la capa de fites...")
        # Check that the point has a photography indicated
        self.check_photo_exists()
        # Check that the photography exists in the photo's folder
        self.check_photo_name()
        # Check that if the point has Z coordinate is a found point
        self.check_cota_fita()

    def check_photo_exists(self):
        """Check that a found point has a photography"""
        # Get a list of points with photography
        photo_exists = self.punt_line_gdf['FOTOS'].notnull()
        points_with_photo = self.punt_line_gdf[photo_exists]
        points_with_photo_list = points_with_photo['ID_PUNT'].to_list()

        points_with_photo_checklist = []
        if self.line_type == 'mtt':
            # Only points that are PPF from official lines
            ppf_with_photo_list = [point_id for point_id in points_with_photo_list if point_id in self.ppf_list]
            points_with_photo_checklist = ppf_with_photo_list
        elif self.line_type == 'rep':
            # All the points from unofficial lines
            points_with_photo_checklist = points_with_photo_list

        # Get a dict with the found points without photography
        found_points_no_photo = {etiqueta: id_punt for (etiqueta, id_punt) in self.found_points_dict.items() if
                                 id_punt not in points_with_photo_checklist}

        if not found_points_no_photo:
            self.logger.info('   Totes les fites trobades tenen fotografia')
        else:
            for etiqueta, point_id in found_points_no_photo.items():
                etiqueta = etiqueta.split('-')[-1]
                point_id = point_id.split('-')[-1]
                self.logger.error(
                    f'   La fita {etiqueta} amb ID PUNT {point_id} és trobada pero no te cap fotografia indicada')

    def check_photo_name(self):
        """Check that the photography in the layer has the same name as de .JPG file"""
        # Get a list with the photographies's filename in the photography folder
        folder_photos_filenames = [f for f in os.listdir(self.photo_folder) if
                                   os.path.isfile(os.path.join(self.photo_folder, f)) and
                                   (f.endswith(".jpg") or f.endswith(".JPG"))]
        # Get a list with the photographies's filename, from PPF if the line is official
        photo_exists = self.punt_line_gdf['FOTOS'].notnull()
        points_with_photo = self.punt_line_gdf[photo_exists]
        found_points_photos = []
        if self.line_type == 'mtt':
            found_points_photos = [feature['FOTOS'] for index, feature in points_with_photo.iterrows() if
                                   feature['ID_PUNT'] in self.ppf_list]
        elif self.line_type == 'rep':
            found_points_photos = [feature['FOTOS'] for index, feature in points_with_photo.iterrows()]
        # Check that the photography in the point layer has the same filename as the photography into the folder
        photos_valid = True
        for photo_filename in found_points_photos:
            if photo_filename not in folder_photos_filenames:
                photos_valid = False
                self.logger.error(f'   La fotografia {photo_filename} no esta a la carpeta de Fotografies')

        if photos_valid:
            self.logger.info('   Totes les fotografies informades a la capa Punt estan a la carpeta de Fotografies')

    def check_cota_fita(self):
        """Check that a point with Z coordinate is found"""
        # Get a list with the PPF that have Z coordinate
        points_z_dict = {}
        for index, feature in self.punt_line_gdf.iterrows():
            etiqueta = feature['ETIQUETA']
            point_id = feature['ID_PUNT']
            z_coord = feature['geometry'].z
            if z_coord > 0 and point_id in self.found_points_dict.values():
                points_z_dict[etiqueta] = point_id
            elif z_coord == 0 and point_id in self.found_points_dict.values():
                etiqueta = etiqueta.split('-')[-1]
                point_id = point_id.split('-')[-1]
                # TODO check if the point has an auxiliary point with z coordinate
                self.logger.error(f'   La F {etiqueta} amb ID PUNT {point_id} es trobada pero no te coordenada Z')

        z_coord_valid = True
        for etiqueta, point_id in points_z_dict.items():
            if point_id not in self.found_points_dict.values():
                z_coord_valid = False
                etiqueta = etiqueta.split('-')[-1]
                point_id = point_id.split('-')[-1]
                self.logger.error(f'   La F {etiqueta} amb ID PUNT {point_id} te coordenada Z pero no es fita trobada')

        if z_coord_valid:
            self.logger.info('   Totes les fites amb coordenada Z son trobades')

    def check_3termes(self):
        """Check 3 terms points"""
        self.logger.info("   Validant el contacte de les fites tres termes...")
        # Get df with points sorted by etiqueta, firstly creating a new sorting column that containts the numbers
        # from the ETIQUETA field as integers, in order to correctly sort the point numbers
        sorted_points_df_temp = self.punt_line_gdf
        etiquetes = sorted_points_df_temp['ETIQUETA'].tolist()
        etiquetes_int = []
        # TODO solo ordenar las fitas que tengan 'F' en su etiqueta, o sea, que sean fitas reales
        for i in etiquetes:
            if i is None:
                i = ''
            point_num = re.search(r'\d+', i)
            if point_num:
                point_num = int(point_num.group())
            etiquetes_int.append(point_num)
        # Add sorting column
        sorted_points_df_temp['sorting'] = etiquetes_int
        # Sort by the new column
        sorted_points_df = sorted_points_df_temp.sort_values(by=['sorting'])
        # Filter by PPF points if official
        if self.line_type == 'mtt':
            ppf_point = sorted_points_df['ID_PUNT'].isin(self.ppf_list)
            sorted_points_df = sorted_points_df[ppf_point]
            if sorted_points_df.empty:
                self.logger.error("   No hi ha punts indicats com Proposta.")
                return
        # Get a list with the contact field from both first and last point
        first_point = sorted_points_df.iloc[0]
        last_point = sorted_points_df.iloc[-1]
        if first_point['CONTACTE'] and last_point['CONTACTE']:
            self.logger.info('      Les fites 3 termes tenen informat el camp CONTACTE')
        else:
            self.logger.error('      Hi ha fites 3 termes que no tenen informat el camp CONTACTE')

        # Recount how many points have the CONTACTE field not empty
        indicated_3t_points = self.punt_line_gdf[self.punt_line_gdf['CONTACTE'].notnull()]
        n_indicated_3t_points = indicated_3t_points.shape[0]
        self.logger.info(f'      Hi ha un total de {n_indicated_3t_points} fites amb el camp CONTACTE informat')

    def check_relation_points_tables(self):
        """Check that all the points that exist in the tables exist in the point layer"""
        self.logger.info('Validant la correspondencia entre les taules i la capa Punt...')
        points_id_list = self.punt_line_gdf['ID_PUNT'].tolist()

        if self.line_type == 'mtt':
            # Check that all the ID_PUNT from P_Proposta exist in the point layer
            p_proposta_valid = True
            for index, feature in self.p_proposta_df.iterrows():
                point_id = feature['ID_PUNT']
                if point_id not in points_id_list:
                    p_proposta_valid = False
                    point_id = point_id.split('-')[-1]
                    self.logger.error(
                        f'   El registre amb ID PUNT {point_id} de la taula P_PROPOSTA no esta a la capa Punt')
            if p_proposta_valid:
                self.logger.info('   Correspondència OK entre els punts de P_PROPOSTA i Punt')

        # Check that all the ID_PUNT from PUNT_FIT exist in the point layer
        punt_fit_valid = True
        for index_, feature_ in self.punt_fit_df.iterrows():
            point_id_ = feature_['ID_PUNT']
            if point_id_ not in points_id_list:
                punt_fit_valid = False
                point_id_ = point_id_.split('-')[-1]
                self.logger.error(f'   El registre amb ID PUNT {point_id_} de la taula PUNT_FIT no esta a la capa Punt')
        if punt_fit_valid:
            self.logger.info('   Correspondencia OK entre els punts de PUNT_FIT i Punt')

    def check_topology(self):
        """Check topology"""
        self.logger.info('Iniciant controls topològics...')
        # Check that the line doesn't crosses or overlaps itself
        self.check_line_crosses_itself()
        # Check that the line doesn't intersect the db lines
        self.check_line_intersects_db()
        # Check that the line doesn't overlaps the db lines
        self.check_line_overlaps_db()
        # Check that the lines endpoints are equal to any point
        self.check_endpoint_covered_point()
        # Check that if a point is not over a line is because it's an auxiliary point
        # This check is not done for unofficial lines because almost the lines have a lot of control points that
        # are not covered by the line.
        if self.line_type == 'mtt': self.check_auxiliary_point()

    def check_line_crosses_itself(self):
        """
        Check that the line doesn't intersects or touches itself. In order to do that, iterates over
        every line's geometry and checks if it crosses any of the other lines
        """
        valid = True
        # Check if some tram does self-intersect
        tram_is_valid = self.tram_line_layer.is_valid
        invalid_features = self.tram_line_layer[~tram_is_valid]
        if not invalid_features.empty:
            valid = False
            for i, invalid_feature in invalid_features.iterrows():
                tram_id = invalid_feature['ID']
                self.logger.error(f"   El tram {tram_id} de la linia s'intersecta o toca a si mateix")
        # Check if some tram intersects another line's tram
        for i, tram in self.tram_line_layer.iterrows():
            line = self.tram_line_layer[self.tram_line_layer['geometry'] != tram['geometry']]
            # Iterates over the other line's trams to check if the curren tram crosses the others
            for i_, tram_ in line.iterrows():
                if tram['geometry'].crosses(tram_['geometry']):
                    valid = False
                    self.logger.error(f'   El tram {tram["ID"]} de la linia talla el '
                                      f'tram {tram_["ID"]} de la mateixa linia')
        if valid:
            self.logger.info("   Els trams de la linia no s'intersecten o toquen a si mateixos")

    def check_line_intersects_db(self):
        """Check that the line doesn't intersects or crosses the database lines"""
        db_line_layer = self.tram_line_mem_gdf if self.line_type == 'mtt' else self.tram_line_rep_gdf
        features_intersects_db = gpd.sjoin(self.tram_line_layer, db_line_layer, op='contains')
        if not features_intersects_db.empty:
            for index, feature in features_intersects_db.iterrows():
                self.logger.error(f"   El tram {feature['ID']} de la linia talla algun tram de la base de dades")
        else:
            self.logger.info('   Els trams de la linia no intersecten cap tram de la base de dades')

    def check_line_overlaps_db(self):
        """Check that the line doesn't overlaps the database lines"""
        db_line_layer = self.tram_line_mem_gdf if self.line_type == 'mtt' else self.tram_line_rep_gdf
        features_overlaps_db = gpd.sjoin(self.tram_line_layer, db_line_layer, op='contains')
        if not features_overlaps_db.empty:
            for index, feature in features_overlaps_db.iterrows():
                self.logger.error(f"   El tram {feature['ID']} de la linia es sobreposa a algun tram de la base de dades")
        else:
            self.logger.info('   Els trams de la linia no es sobreposen a cap tram de la base de dades')

    def check_endpoint_covered_point(self):
        """Check that the coordinates of the lines endpoints are equal to any point"""
        # Check if the lines endpoints coordinates are equal to any point
        endpoint_covered = True
        for index, feature in self.tram_line_layer.iterrows():
            tram_id = feature['ID_TRAM']
            # Get endpoints coordinates
            first_endpoint_no_rounded = feature['geometry'].coords[0]
            last_endpoint_no_rounded = feature['geometry'].coords[-1]
            # Rount them if the line is official
            first_endpoint, last_endpoint = None, None
            if self.line_type == 'mtt':
                first_endpoint = (round(first_endpoint_no_rounded[0], 1), round(first_endpoint_no_rounded[1], 1))
                last_endpoint = (round(last_endpoint_no_rounded[0], 1), round(last_endpoint_no_rounded[1], 1))
            elif self.line_type == 'rep':
                first_endpoint = first_endpoint_no_rounded
                last_endpoint = last_endpoint_no_rounded

            if (first_endpoint or last_endpoint) not in self.points_coords_dict.values():
                endpoint_covered = False
                self.logger.error(f'   Algun dels punts finals del tram {tram_id} no coincideixen amb una fita de la capa Punt')

        if endpoint_covered:
            self.logger.info('   Tots els punts finals dels trams de la linia coincideixen amb una fita de la capa Punt')

    def get_point_coordinates(self):
        """
        Get a dict of the points ID and coordinates, and round them to 1 decimal if the line is official
        :return: points_coord_dict - Dict of points coordinates with format (x, y)
        """
        # Get ID
        points_id = self.punt_line_gdf['ID_PUNT'].tolist()
        # Get coordinates
        x_coords_no_round_list = self.punt_line_gdf['geometry'].x.tolist()
        y_coords_no_round_list = self.punt_line_gdf['geometry'].y.tolist()
        # Round the coordinates if the line is official
        x_coords_list, y_coords_list = None, None
        if self.line_type == 'mtt':
            x_coords_list = [round(x, 1) for x in x_coords_no_round_list]
            y_coords_list = [round(y, 1) for y in y_coords_no_round_list]
        elif self.line_type == 'rep':
            x_coords_list = x_coords_no_round_list
            y_coords_list = y_coords_no_round_list
        # Get list with the points coordinates
        points_coord_list = list(zip(x_coords_list, y_coords_list))
        # Enrich list with the point id and convert to dict
        points_coord_dict = dict(zip(points_id, points_coord_list))

        return points_coord_dict

    def check_auxiliary_point(self):
        """
        Check if a point that is not covered by the line is an auxiliary point
        """
        # Check if the point is covered by the line
        for point_id, point_coords in self.points_coords_dict.items():
            if point_coords not in self.line_coords_list:  # Check if the point coordinates are not covered by the line
                if point_id in self.ppf_list:  # Check if the point is a ppf point
                    point = self.punt_fit_df.loc[self.punt_fit_df['ID_PUNT'] == point_id]
                    aux = point['AUX'].values
                    if len(aux) < 1:
                        return
                    aux = aux[0]
                    n_fita = point['ID_FITA'].values[0]
                    point_id = point_id.split('-')[-1]
                    if aux == '1':
                        self.logger.info(f'   La fita F {n_fita} amb ID PUNT {point_id} no esta a sobre de la linia pero es auxiliar')
                    else:
                        self.logger.error(f'   La fita F {n_fita} amb ID PUNT {point_id} no esta a sobre de la linia i NO es auxiliar')

    def get_line_coordinates(self):
        """
        Get a list with the line's coordinates, and round them to 1 decimal if the line is official
        :return: line_coords_list - List with the line's coordinates
        """
        line_coords_no_rounded = []
        trams = self.tram_line_layer['geometry'].tolist()
        for t in trams:
            if t is None:
                self.logger.error(f"   Existeix algun tram sense coordenades. Si us plau, elimina'l")
            else:
                tram_coords = t.coords
                for v in tram_coords:
                    line_coords_no_rounded.append(v)

        line_coords_list = None
        if self.line_type == 'mtt':
            line_coords_list = [(round(x, 1), round(y, 1)) for x, y in line_coords_no_rounded]
        elif self.line_type == 'rep':
            line_coords_list = line_coords_no_rounded

        return line_coords_list

    def write_first_report(self):
        """Write log's header"""
        line_type = 'Memòria dels Treballs Topogràfics' if self.line_type == 'mtt' else 'Replantejament'
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_path, "a") as f:
            f.write("\tProces: Control de qualitat d'una linia\n")
            f.write(f"\tData: {date}\n")
            f.write(f"\tID linia: {self.line_id}\n")
            f.write(f"\tTipus linia: {line_type}\n")
            f.write("\n")

    def rm_temp(self):
        """Remove temporal files from the workspace"""
        gpkg = gdal.OpenEx(WORK_GPKG, gdal.OF_UPDATE, allowed_drivers=['GPKG'])
        for layer in TEMP_ENTITIES:
            layer_name = layer.split('.')[0]
            gpkg.ExecuteSQL(f'DROP TABLE {layer_name}')

        self.logger.info('   Arxius temporals esborrats')

    def rm_working_directory(self):
        """Remove temporal local line directory"""
        shutil.rmtree(self.line_folder)

    def create_error_response(self, message):
        """Create a error JSON for the response data"""
        self.logger.error(message)
        self.response_data['result'] = 'error'
        self.response_data['message'] = message
        logging.shutdown()

        return {'response': self.response_data}

    def add_response_data(self):
        """Add the log's reports to the JSON response data"""
        report_list = []
        with open(self.log_path, 'r') as f:
            reports = f.read().splitlines()  # Avoid reading with newline character
            for report in reports:
                report_split = report.split(' - ')
                if len(report_split) == 1:
                    report_level = 'INFO'
                    report_info = report_split[0]
                else:
                    report_date, report_level, report_info = report_split[0], report_split[1], report_split[2]
                item = {
                    'level': report_level,
                    'report_message': report_info
                }
                report_list.append(item)
        self.response_data['reports'] = report_list
        logging.shutdown()

        return {'response': self.response_data}

    def reset_logger(self):
        """
        Reset all the loggers handlers and config in order to avoid maintaining it and modifying the later reports
        """
        for h in self.logger.handlers:
            self.logger.removeHandler(h)
        logging.shutdown()


def render_qa_page(request):
    """
    Render the same qa page itself
    :param request: Http request
    :return: Rendering of the qa page
    """
    return render(request, '../templates/qa_page.html')


def render_report_page(request):
    """
    Render the report page with the response created
    :param request: Http request
    :return: Rendering of the report page
    """
    response = request.session['response']
    return render(request, '../templates/qa_reports.html', response)
