# -*- coding: utf-8 -*-

# ----------------------------------------------------------
# TERRITORIAL DELIMITATION TOOLS (ICGC)
# Authors: Cesc Masdeu & Fran Martin
# Version: 0.1
# Date: 20201103
# Version Python: 3.7
# ----------------------------------------------------------

# TODO comprovar amb capes que tinguin errors

"""
Quality check of a line ready to upload to the database
"""

# Standard library imports
import os
import os.path as path
import decimal
from datetime import datetime
import logging
import re

# Third party imports
import geopandas as gpd
from osgeo import gdal
from django.http import JsonResponse
from django.views import View

# Local imports
from CQline.config import *


class CheckQualityLine(View):
    """
    Class for checking a line's geometry and attributes quality previous to upload it into the database
    """

    def __init__(self, **kwargs):
        """
        All the attributes are assigned to None and initialized into other methods
        """
        super().__init__(**kwargs)
        # Environment parameters
        self.line_id = None
        self.line_id_txt = None
        self.current_date = None
        self.logger = None
        self.ppf_list = None
        # Paths to directories and folders
        self.line_folder = None
        self.doc_delim = None
        self.carto_folder = None
        self.tables_folder = None
        # Geodataframes for data managing
        self.lin_tram_ppta_sidm2_gdf = None
        self.fita_g_sidm2_gdf = None
        self.lin_tram_ppta_line_gdf = None
        self.punt_line_gdf = None
        self.p_proposta_gdf = None
        self.punt_fit = None

    def get(self, request, line_id):
        """
        Main entry point. Here is where the magic is done. This method is called when someone wants to init the process of quality
        checking and is supposed to prepare the workspace, prepare the line and check it's geometry and attributes
        """
        # SET UP THE WORKING ENVIRONMENT -------------------------
        # Set up parameters
        self.set_up(line_id)
        # Check and set directories paths
        directory_tree_valid = self.check_directories()
        if directory_tree_valid:
            self.set_directories()
        else:
            return
        # Delete temp files from the workspace
        self.rm_temp()
        # Copy layers and tables from line's folder to the workspace
        entities_exist = self.check_entities_exist()
        if not entities_exist:
            return
        self.copy_data_2_gpkg()
        self.set_layers_gdf()
        # Create list with only points that are "Proposta Final"
        self.ppf_list = self.get_ppf_list()

        # START CHECKING ------------------------------------------
        # Check if the line ID already exists into the database
        self.check_line_id_exists()
        # Check if the line's field structure and content is correct
        self.check_lin_tram_ppta_layer()
        # Check the line and point's geometry
        self.check_layers_geometry()
        # Get info from the parts and vertexs of every line tram
        self.info_vertexs_line()
        # Check that the points are correctly rounded
        self.check_points_decimals()
        # Get info and check the features in P_Proposta
        self.info_p_proposta()
        # Check that an auxiliary point has correctly indicated its real point's ID
        self.check_aux_id()

        # Comprovar diferents aspectes de les fites trobades
        # TODO
        # self.check_fites_trobades()
        '''
        # Comprovar les fites 3 termes
        self.check_3termes()

        # Comprovar la correspondència entre taules i capes
        self.check_corresp_fites_taules()

        # Fer els controls topològics
        self.check_topology()
        '''

        return JsonResponse({'data': '-- Linia {} checkejada --\n'.format(line_id)})

    def set_up(self, line_id):
        """
        Set up the environment parameters that the class would need
        :param line_id: line ID from the line the class is going to check
        """
        # Set line ID
        self.line_id = line_id
        # Convert line ID from integer to string nnnn
        self.line_id_txt = self.line_id_2_txt()
        # Get current date and time
        self.current_date = datetime.now().strftime("%Y%m%d-%H%M")
        # Configure logger
        self.logger = logging.getLogger()
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
        log_name = f"ReportCQ_{self.line_id_txt}_{self.current_date}.txt"
        # log_path = os.path.join(LINES_DIR, str(self.line_id), WORK_REC_DIR, log_name)
        log_path = os.path.join(LOG_DIR, log_name)
        file_handler = logging.FileHandler(filename=log_path, mode='w')
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)

    def check_directories(self):
        """Check if the directory tree structure and content is correct"""
        tree_valid = True

        line_folder = os.path.join(UPLOAD_DIR, str(self.line_id))
        if path.exists(line_folder):  # Check if the line folder exists at the loading folder
            self.line_folder = line_folder
            doc_delim = os.path.join(self.line_folder, 'DocDelim')
            if path.exists(doc_delim):  # Check the DocDelim folder exists
                self.doc_delim = doc_delim
                for sub_dir in SUB_DIR_LIST:  # Check if all the subdirs exist
                    if sub_dir not in os.listdir(self.doc_delim):
                        tree_valid = False
                        self.logger.error(f'No existeix el subdirectori {sub_dir}')
            else:
                self.logger.error('No existeix DocDelim dins el directori de la línia')
                tree_valid = False
        else:
            self.logger.error('No existeix la línia al directori de càrrega')
            tree_valid = False

        if tree_valid:
            self.logger.info('Estructura de directoris OK')

        return tree_valid

    def set_directories(self):
        """Set paths to directories"""
        self.carto_folder = os.path.join(self.doc_delim, 'Cartografia')
        self.tables_folder = os.path.join(self.doc_delim, 'Taules')

    def set_layers_gdf(self):
        """
        Open all the necessary layers as geodataframes with geopandas
        :return:
        """
        # SIDM2
        self.lin_tram_ppta_sidm2_gdf = gpd.read_file(WORK_GPKG, layer='Lin_Tram_Proposta_SIDM2')
        self.fita_g_sidm2_gdf = gpd.read_file(WORK_GPKG, layer='Fita_G_SIDM2')
        # Line
        self.lin_tram_ppta_line_gdf = gpd.read_file(WORK_GPKG, layer='Lin_TramPpta')
        self.punt_line_gdf = gpd.read_file(WORK_GPKG, layer='Punt')
        # Tables
        self.p_proposta_gdf = gpd.read_file(WORK_GPKG, layer='P_Proposta')
        self.punt_fit = gpd.read_file(WORK_GPKG, layer='PUNT_FIT')

    def line_id_2_txt(self):
        """
        Convert line id (integer) to string nnnn
        :return: line_id_txt -> <string> ID de la línia introduit en format text
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

    def check_entities_exist(self):
        """
        Check if all the necessary shapefiles and tables exists
        :return:
        """
        entities_exist = False
        for shape in SHAPES_LIST:
            shape_path = os.path.join(self.carto_folder, shape)
            if path.exists(shape_path):
                shapes_exist = True
            else:
                shapes_exist = False

        for dbf in TABLE_LIST:
            dbf_path = os.path.join(self.tables_folder, dbf)
            if path.exists(dbf_path):
                entities_exist = True
            else:
                entities_exist = False

        if not entities_exist:
            self.logger.error('No existeixen les capes i taules necessaries a DocDelim')

        return entities_exist

    def copy_data_2_gpkg(self):
        """Copy all the feature classes and tables from the line's folder to the local work geopackage"""
        for shape in SHAPES_LIST:
            shape_name = shape.split('.')[0]
            shape_path = os.path.join(self.carto_folder, shape)
            try:
                shape_gdf = gpd.read_file(shape_path)
                shape_gdf.to_file(WORK_GPKG, layer=shape_name, driver="GPKG")
            except:
                self.logger.error(f"No s'ha pogut copiar la capa {shape_name}")
                return

        for dbf in TABLE_LIST:
            dbf_name = dbf.split('.')[0]
            dbf_path = os.path.join(self.tables_folder, dbf)
            try:
                dbf_gdf = gpd.read_file(dbf_path)
                dbf_gdf.to_file(WORK_GPKG, layer=dbf_name, driver="GPKG")
            except:
                self.logger.error(f"No s'ha pogut copiar la taula {dbf_name}")
                return

        self.logger.info(f"Capes i taules de la línia {self.line_id} copiades correctament a CQline.gpkg")

    def check_line_id_exists(self):
        """
        Check if the line ID already exists into the database, both into Fita_G and Lin_Tram_Proposta
        """
        line_id_in_lin_tram = False
        line_id_in_fita_g = False

        # Check into LIN_TRAM_PROPOSTA_SIDM2
        tram_duplicated_id = self.lin_tram_ppta_sidm2_gdf['ID_LINIA'] == self.line_id
        tram_line_id = self.lin_tram_ppta_sidm2_gdf[tram_duplicated_id]
        if tram_line_id.shape[0] > 0:
            line_id_in_lin_tram = True

        # Check into FITA_G_SIDM2
        fita_g_duplicated_id = self.fita_g_sidm2_gdf['ID_LINIA'] == self.line_id
        fita_g_line_id = self.fita_g_sidm2_gdf[fita_g_duplicated_id]
        if fita_g_line_id.shape[0] > 0:
            line_id_in_fita_g = True

        if line_id_in_fita_g and line_id_in_lin_tram:
            self.logger.error("L'ID Linia introduït està en FitaG i Lin_Tram_Proposta")
        elif line_id_in_fita_g and not line_id_in_lin_tram:
            self.logger.error("L'ID Linia introduït està en FitaG però no en Lin_Tram_Proposta")
        elif not line_id_in_fita_g and line_id_in_lin_tram:
            self.logger.error("L'ID Linia introduït no està en FitaG però sí en Lin_Tram_Proposta")
        elif not line_id_in_fita_g and not line_id_in_lin_tram:
            self.logger.info("L'ID Linia no està repetit a SIDM2")

    def check_lin_tram_ppta_layer(self):
        """
        Check line's layer's field structure and content
        :return:
        """
        self.check_fields_lin_tram_ppta()
        self.check_fields_content_lint_tram_ppta()

    def check_fields_lin_tram_ppta(self):
        """Check line's layer's field structure is correct"""
        # Fields that the line's layer must have
        true_fields = ('OBJECTID', 'ID_LINIA', 'ID', 'DATA', 'COMENTARI', 'P1', 'P2', 'P3', 'P4', 'PF',
                       'ID_FITA1', 'ID_FITA2', 'geometry')

        # Get line's layer's fields
        lin_tram_ppta_line_gdf = gpd.read_file(WORK_GPKG, layer='Lin_TramPpta')
        lin_tram_fields = list(lin_tram_ppta_line_gdf.columns)

        # Compare
        field_match = 0
        for field in lin_tram_fields:
            if field in true_fields:
                field_match += 1

        if field_match == len(true_fields):
            self.logger.info("L'estructura de camps de Lin_TramPpta és correcte")
        else:
            self.logger.error("L'estructura de camps de Lin_TramPpta NO és correcte")

    def check_fields_content_lint_tram_ppta(self):
        """Check line's layer's content is correct"""
        # Check that doesn't exist the line ID from another line
        line_id_error = False
        not_line_id = self.lin_tram_ppta_line_gdf['ID_LINIA'] != self.line_id
        tram_not_line_id = self.lin_tram_ppta_line_gdf[not_line_id]
        if tram_not_line_id.shape[0] > 1 and not line_id_error:
            line_id_error = True
            self.logger.error("Existeixen trams de línia amb l'ID_LINIA d'una altra línia")

        # Check that the fita ID is correct
        id_fita_error = False
        # F1
        id_f1_bad = self.lin_tram_ppta_line_gdf['ID_FITA1'] == 1
        tram_id_f1_bad = self.lin_tram_ppta_line_gdf[id_f1_bad]
        # F2
        id_f2_bad = self.lin_tram_ppta_line_gdf['ID_FITA2'] == 1
        tram_id_f2_bad = self.lin_tram_ppta_line_gdf[id_f2_bad]

        if (tram_id_f1_bad.shape[0] > 1 or tram_id_f2_bad.shape[0] > 1) and not id_fita_error:
            id_fita_error = True
            self.logger.error("El camp ID_FITA d'algun dels trams de la línia no és vàlid")

        if not line_id_error and not id_fita_error:
            self.logger.info("Els camps de Lin_TramPpta estan correctament emplenats")

    def get_ppf_list(self):
        """
        Get list with the ID of the only points that are "Punt Proposta Final", as known as "PPF"
        :return: ppf_list - List with the ID of the PPF
        """
        is_ppf = self.p_proposta_gdf['PFF'] == 1
        ppf = self.p_proposta_gdf[is_ppf]
        ppf_list = ppf['ID_PUNT'].to_list()

        return ppf_list

    def check_layers_geometry(self):
        """
        Check the geometry of both line and points
        """
        self.logger.info('Comprovació de les geometries')
        self.logger.info('Lin_Tram_Proposta :')
        self.check_lin_tram_geometry()
        self.logger.info('Punt :')
        self.check_points_geometry()

    def check_lin_tram_geometry(self):
        """Check the line's geometry"""
        error = False
        # Check if there are empty features
        is_empty = self.lin_tram_ppta_line_gdf.is_empty
        empty_features = self.lin_tram_ppta_line_gdf[is_empty]
        if empty_features.shape[0] > 0:
            error = True
            for index, feature in empty_features.iterrows():
                tram_id = feature['ID']
                self.logger.error(f'      El tram {tram_id} està buit')
        # Check if there is a ring
        is_ring = self.lin_tram_ppta_line_gdf.is_empty
        ring_features = self.lin_tram_ppta_line_gdf[is_ring]
        if ring_features.shape[0] > 0:
            error = True
            for index, feature in ring_features.iterrows():
                tram_id = feature['ID']
                self.logger.error(f'      El tram {tram_id} té un anell interior')
        # Check if the geometry is valid
        is_valid = self.lin_tram_ppta_line_gdf.is_valid
        invalid_features = self.lin_tram_ppta_line_gdf[~is_valid]
        if invalid_features.shape[0] > 0:
            error = True
            for index, feature in invalid_features.iterrows():
                tram_id = feature['ID']
                self.logger.error(f'      El tram {tram_id} no té una geometria vàlida')
        # Check if the line is multi-part and count the parts in that case
        for index, feature in self.lin_tram_ppta_line_gdf.iterrows():
            geom_type = feature['geometry'].geom_type
            if geom_type == 'MultiLineString':
                error = True
                tram_id = feature['ID']
                n_parts = feature['geometry'].geoms
                self.logger.error(f'      El tram {tram_id} és multi-part i té {n_parts} parts')

        if not error:
            self.logger.info("      No s'ha detectat cap error de geometria a Lin_TramPpta")

    def check_points_geometry(self):
        """Check the points' geometry"""
        error = False
        # Check if there are empty features
        is_empty = self.punt_line_gdf.is_empty
        empty_features = self.punt_line_gdf[is_empty]
        if empty_features.shape[0] > 0:
            error = True
            for index, feature in empty_features.iterrows():
                point_id = feature['ID_PUNT']
                self.logger.error(f'      El punt {point_id} està buit')
        # Check if the geometry is valid
        is_valid = self.punt_line_gdf.is_valid
        invalid_features = self.punt_line_gdf[~is_valid]
        if invalid_features.shape[0] > 0:
            error = True
            for index, feature in invalid_features.iterrows():
                point_id = feature['ID_PUNT']
                self.logger.error(f'      El punt {point_id} no té una geometria vàlida')

        if not error:
            self.logger.info("      No s'ha detectat cap error de geometria a la capa Punt")

    def info_vertexs_line(self):
        """Get info and make a recount of the line's vertexs"""
        self.logger.info('Vèrtexs de la línia:')
        self.logger.info('+---------+-----------+')
        self.logger.info('| Tram ID | Nº vèrtex |')
        self.logger.info('+---------+-----------+')

        for index, feature in self.lin_tram_ppta_line_gdf.iterrows():
            tram_id = feature['ID']
            tram_vertexs = len(feature['geometry'].coords)   # Nº of vertexs that compose the tram
            self.logger.info(f"|    {tram_id}   |     {tram_vertexs}     |")
            self.logger.info('+---------+-----------+')

    def check_points_decimals(self):
        """Check if the points's decimals are correct and are rounded to 1 decimal"""
        decim_valid = True
        for index, feature in self.punt_line_gdf.iterrows():
            # Point parameters
            point_etiqueta = feature['ETIQUETA']
            point_id = feature['ID_PUNT']
            point_x = feature['geometry'].x
            point_y = feature['geometry'].y
            # Check if rounded correctly
            dif_x = abs(point_x - round(point_x, 1))
            dif_y = abs(point_y - round(point_y, 1))
            if dif_x > 0.01 or dif_y > 0.01:
                decim_valid = False
                self.logger.error(f"El punt de la fita {point_id} | {point_etiqueta} no està correctament decimetritzat")

        if decim_valid:
            self.logger.info('Les fites estan correctament decimetritzades')

    def info_p_proposta(self):
        """
        Get info and check the points in the table P_Proposta, like:
            - Count the points and distinguish them depending on its type
            - Check that the field ORDPF is not NULL
            - Check that an auxiliary point is not indicated as a real point
        """
        self.logger.info('Informació de les fites :')
        # Count the points in the table P_Proposta depending on the point's type
        self.count_points()
        # Check that ORDPF is not null
        ordpf_valid = self.check_ordpf()
        # Check that the points in P_Proposta are correctly indicated
        real_points_valid = self.check_real_points()
        if ordpf_valid and real_points_valid:
            self.logger.info(f'Tots els registre de la taula P_Proposta són vàlids')

    def count_points(self):
        """Count the points in the table P_Proposta and distinguish them depending on its type"""
        # Not final points
        # PFF = 0
        not_ppf = self.p_proposta_gdf['PFF'] == 0
        not_final_points = self.p_proposta_gdf[not_ppf]
        n_not_final_points = not_final_points.shape[0]
        # Real points
        # PFF = 1 AND ESFITA = 1
        proposta_points = self.p_proposta_gdf.loc[(self.p_proposta_gdf['PFF'] == 1) & (self.p_proposta_gdf['ESFITA'] == 1)]
        n_proposta_points = proposta_points.shape[0]
        # Auxiliary points
        # PFF = 1 AND ESFITA = 0
        auxiliary_points = self.p_proposta_gdf.loc[(self.p_proposta_gdf['PFF'] == 1) & (self.p_proposta_gdf['ESFITA'] == 0)]
        n_auxiliary_points = auxiliary_points.shape[0]

        self.logger.info(f'      Fites PPF reals: {n_proposta_points}')
        self.logger.info(f'      Fites PPF auxiliars: {n_auxiliary_points}')
        self.logger.info(f'      Fites no finals: {n_not_final_points}')

    def check_ordpf(self):
        """Check the field ORDPF is not NULL"""
        valid = True
        ordpf_null = self.p_proposta_gdf['ORDPF'].isnull()
        points_ordpf_null = self.p_proposta_gdf[ordpf_null]

        if points_ordpf_null.shape[0] > 0:
            valid = False
            for index, feature in points_ordpf_null.iterrows():
                point_id = feature['ID_PUNT']
                self.logger.error(f"      El camp ORDPF del punt {point_id} és nul")

        return valid

    def check_real_points(self):
        """Check that an auxiliary point is not indicated as a real point"""
        # If PPF = 1 and ORDPF = 0 => ESFITA MUST BE 0
        valid = True
        bad_auxiliary_points = self.p_proposta_gdf.loc[(self.p_proposta_gdf['PFF'] == 1) &
                                                       (self.p_proposta_gdf['ORDPF'] == 0) &
                                                       (self.p_proposta_gdf['ESFITA'] != 0)]

        if bad_auxiliary_points.shape[0] > 0:
            valid = False
            for index, feature in bad_auxiliary_points.iterrows():
                point_id = feature['ID_PUNT']
                self.logger.error(f"      El punt {point_id} està mal indicat a P_Proposta.")

        return valid

    def check_aux_id(self):
        """Check that an auxiliary point has correctly indicated its real point's ID"""
        real_points = self.punt_fit[self.punt_fit['AUX'] == '0']
        auxiliary_points = self.punt_fit[self.punt_fit['AUX'] == '1']
        auxiliary_points_id_list = auxiliary_points['ID_PUNT'].to_list()

        for aux_id in auxiliary_points_id_list:
            if aux_id not in real_points.values:
                self.logger.error(F"      La fita auxiliar {aux_id} no té correctament indicat l'ID de la fita real"

    def check_fites_trobades(self):
        """
        Funció per a comprovar diferents aspectes de les fites trobades, com són:
            - Que tinguin fotografia
            - Que la fotografia existeixi a la carpeta corresponent
            - Que si té cota indicada sigui fita trobada
        """
        # Comprovar que la fita trobada té fotografia informada
        self.check_foto_exists()
        # Comprovar que la foto existeix a la carpeta de fotografies
        self.check_name_fotos()
        # Comprovar que si la fita té cota sigui fita trobada
        self.check_cota_fita()

    def check_foto_exists(self):
        """Funció per a comprovar que una fita trobada té fotografia informada"""
        # Crear llista de fites amb fotos
        sql_fites_fotos = "WHERE FOTOS <> ''"
        with arcpy.da.SearchCursor(PUNT, "ID_PUNT", sql_clause=(None, sql_fites_fotos)) as cursor:
            llista_fites_fotos = [id_punt for id_punt in cursor]
        # Comprovar que les fites trobades tenen fotografia
        llista_fites_sense_foto = []
        sql_fites_trobades = "WHERE TROBADA = '1'"
        with arcpy.da.SearchCursor(PUNT_FIT, "ID_PUNT", sql_clause=(None, sql_fites_trobades)) as cursor:
            llista_fites_sense_foto = [id_punt for id_punt in cursor if id_punt not in llista_fites_fotos]

        # Comprovar que les fites trobades tenen fotografia informada
        if not llista_fites_sense_foto:
            self.write_report("Concordança entre el camp TROBADA i el camp FOTOGRAFIA, OK", "ok")
        else:
            for id_punt in llista_fites_sense_foto:
                self.write_report('La fita {} és trobada però no té cap fotografia indicada'.format(id_punt), "error")

    def check_name_fotos(self):
        """Funció per a comprovar que la fotografia informada té el mateix nom que el fitxer .JPG"""
        # subdirectoris en funció de l'idLinia:
        linia_folder = DIR_ENTRADA + "\\" + str(self.id_linia_num)
        foto_folder = linia_folder + '/DocDelim/Fotografies'
        llista_fotos_folder = []  # Llista amb les fotografies que hi ha a la carpeta

        # Construir llista amb els noms de les fotografies que hi ha a la carpeta
        for dirpath, dirnames, datatypes in os.walk(foto_folder):
            for foto in datatypes:
                if foto.endswith(".jpg") or foto.endswith(".JPG"):
                    llista_fotos_folder.append(foto)

        # Construir llista amb els noms de les fotografies que hi ha a la fc
        sql_fites_fotos = "FOTOS <> ''"
        # Llista amb les fotografies que hi ha indicades a la FC Punt i són de fites Proposta final
        llista_fotos_fc = []
        try:
            with arcpy.da.SearchCursor(PUNT, field_names=["ID_PUNT", "FOTOS"],
                                       where_clause=sql_fites_fotos) as cursor:
                for id_punt, foto in cursor:
                    if id_punt in self.llista_punts_ppta:
                        llista_fotos_fc.append(foto)
        except:
            self.write_report("No s'han pogut comprovar les fites amb fotografia de la FC Punt", "error")

        # Comprovar que la fotografia informada té el mateix nom que el fitxer JPG
        for nomfoto in llista_fotos_fc:
            if nomfoto not in llista_fotos_folder:
                self.write_report("{0} no està a la carpeta de Fotografies".format(nomfoto), "error")
            else:
                self.write_report("{0} està a la carpeta de Fotografies".format(nomfoto), "ok")

    def check_cota_fita(self):
        """Funció per a comprovar que una fita amb cota és trobada"""
        msg = "No s'ha pogut comprovar si les fites amb coordenada Z són trobades"

        # Crear llista de fites de la fc punt que tenen cota indicada
        llista_fites_cota = []
        try:
            with arcpy.da.SearchCursor(PUNT, field_names=["ID_PUNT", "SHAPE@Z"]) as cursor:
                for row in cursor:
                    if row[1] != 0 and row[0] in self.llista_punts_ppta:
                        llista_fites_cota.append(row[0])
        except:
            self.write_report(msg, "error")

        # Crear llista de fites de la taula PUNT_FIT que són trobades
        llista_fites_trobades = []
        try:
            sql_fites_trobades = "TROBADA = '1'"
            with arcpy.da.SearchCursor(PUNT_FIT, field_names="ID_PUNT", where_clause=sql_fites_trobades) as cursor:
                for row in cursor:
                    llista_fites_trobades.append(row[0])
        except:
            self.write_report(msg, "error")

        # Comprovar que les fites amb cota estan indicades com a trobades
        try:
            for fita in llista_fites_cota:
                if fita not in llista_fites_trobades:
                    self.write_report("El punt {0} té coordenada Z però no és fita trobada".format(fita), "error")
                else:
                    self.write_report('El punt {0} té coordenada Z i és fita trobada'.format(fita), "ok")
        except:
            self.write_report(msg, "error")

    def check_3termes(self):
        """Funció per a comprovar les fites 3 termes"""
        msg = ("Les F3T tenen informat el camp CONTACTE", "Hi ha fites 3 termes sense contacte")

        # Crear un camp nou a la capa punt per a poder ordenar-la correctament
        arcpy.AddField_management(PUNT, "ORDRE", "SHORT")

        with arcpy.da.UpdateCursor(PUNT, field_names=("ID_PUNT", "ETIQUETA", "ORDRE")) as cursor:
            for row in cursor:
                if row[0] in self.llista_punts_ppta:
                    etiqueta = row[1]
                    # Comprovar si l'etiqueta del punt conté "aux", "AUX" o "Aux"
                    aux_exists = re.search('aux', etiqueta.lower())
                    if aux_exists is None:
                        row[2] = int(re.findall(r'\d+', etiqueta)[0])
                        cursor.updateRow(row)

        llista_contacte = []  # LLista amb el contingut dels camps de contacte
        with arcpy.da.SearchCursor(PUNT,
                                   field_names=("ID_PUNT", "CONTACTE",
                                                "ETIQUETA", "ORDRE"), sql_clause=(None,
                                                                                  "ORDER BY ORDRE ASC")) as cursor:
            for row in cursor:
                if row[0] in self.llista_punts_ppta and row[3]:
                    llista_contacte.append(row[1])

        # Comprovar si la primera i l'última fita de la línia tenen text al camp de contacte
        if len(llista_contacte[0]) > 1 and len(llista_contacte[-1]) > 1:
            self.write_report(msg[0], "ok")
        else:
            self.write_report(msg[1], "error")

        # Fer un recompte del nº de fites que tenen el camp de contacte amb text
        n_contacte = 0
        for camp in llista_contacte:
            if len(camp) > 1:
                n_contacte += 1
        n_contacte = str(n_contacte)
        missatge_ok2 = "Hi ha un total de {0} fites amb el camp CONTACTE informat".format(n_contacte)
        self.write_report(missatge_ok2, "ok")

        arcpy.DeleteField_management(PUNT, "ORDRE")  # Eliminar el camp d'ordre creat

    def check_corresp_fites_taules(self):
        """Funció per a comprovar la correspondencia entre taules i capes segons ID_PUNT"""
        msg = ("Correspondència OK entre els punts de P_PROPOSTA i PUNT",
               "Correspondència OK entre els punts de PUNT_FIT i PUNT")

        llista_punts = []  # Llista amb tots els ID_PUNT de la capa Punt
        with arcpy.da.SearchCursor(PUNT, "ID_PUNT") as cursor:
            for row in cursor:
                llista_punts.append(row)

        # Comprovar que tots els ID_PUNT de P_Proposta estan a la capa Punt
        # report_info("Comprovant correspondència P_Proposta amb Punt...")
        val_ok3 = 0
        with arcpy.da.SearchCursor(PUNT_PROPOSTA, "ID_PUNT") as cursor:
            for row in cursor:
                if row not in llista_punts:
                    missatge_bad1 = "El punt {0} de P_PROPOSTA no està a la capa PUNT".format(row[0])
                    self.write_report(missatge_bad1, "error")
                    val_ok3 = 1
        if val_ok3 == 0:
            self.write_report(msg[0], "ok")

        # Comprovar que tots els ID_PUNT de PUNT_FIT estan a la capa Punt
        # report_info("Comprovant correspondència PUNT_FIT amb PUNT...")
        val_ok4 = 0
        with arcpy.da.SearchCursor(PUNT_FIT, "ID_PUNT") as cursor:
            for row in cursor:
                if row not in llista_punts:
                    self.write_report("El punt {0} de PUN_FIT no està a la capa PUNT".format(row[0]),
                                      "error")
                    val_ok4 = 1
        if val_ok4 == 0:
            self.write_report(msg[1], "ok")

    def check_topology(self):
        """Funció per a fer els controls topologics"""
        # Exportar les fc punt i linTramPpta
        arcpy.FeatureClassToFeatureClass_conversion(PUNT, ESQUEMA_CQLINIA_LINIA, "Punt_linia")
        arcpy.FeatureClassToFeatureClass_conversion(LIN_TRAM_PPTA, ESQUEMA_CQLINIA_LINIA, "Lin_TramPpta_linia")

        # Controls topològics de la mateixa línia
        self.check_topology_line()

        # Controls topològics de la linia amb la base general
        self.check_topology_gdb()

    def check_topology_line(self):
        """Funció per a fer els controls topològics de la mateixa linia"""
        msg = ("Topologia de la linia creada i validada. Revisa els errors topològics",
               "No s'ha pogut crear la topologia de la linia", "No s'han pogut afegir les FC a la topologia",
               "No s'han pogut afegir les regles a la topologia", "No s'ha pogut validar la topologia")

        # Variables d'entrada
        topo_nom = "CQlinia_Topology_linia"
        cluster_tol = 0.001

        # Llista amb les fc de la topologia
        fc_topologia_linia = (PUNT_LINIA, LIN_TRAM_PPTA_LINIA)

        # Crear la topologia
        try:
            if not arcpy.Exists(TOPOLOGIA_LINIA):
                arcpy.CreateTopology_management(ESQUEMA_CQLINIA_LINIA, topo_nom, cluster_tol)
                print("-- Topologia de la linia creada. Iniciant controls topologics... ------------")
            else:
                arcpy.Delete_management(TOPOLOGIA_LINIA)
                arcpy.CreateTopology_management(ESQUEMA_CQLINIA_LINIA, topo_nom, cluster_tol)
                print("-- Topologia de la linia creada. Iniciant controls topologics... ------------")
        except:
            self.write_report(msg[1], "error")

        # Afegir les fc a la topologia
        try:
            for fc in fc_topologia_linia:
                arcpy.AddFeatureClassToTopology_management(TOPOLOGIA_LINIA, fc)
            print("     FC afegides a la topologia...")
        except:
            self.write_report(msg[2], "error")

        # Afegir regles de topologia
        topology_rules_self_line = (
            # Els trams han d'acabar sempre en una fita
            (TOPOLOGIA_LINIA, "Endpoint Must Be Covered By (Line-Point)", LIN_TRAM_PPTA_LINIA, "", PUNT_LINIA, ""),
            # Una fita no pot estar sobre un tram
            (TOPOLOGIA_LINIA, "Must Be Covered By (Point-Line)", PUNT_LINIA, "", LIN_TRAM_PPTA_LINIA, ""),
            # No pot haver sobre posició entre trams
            (TOPOLOGIA_LINIA, "Must Not Overlap (Line)", LIN_TRAM_PPTA_LINIA, "", "", ""),
            # No pot haver intersecció entre trams
            (TOPOLOGIA_LINIA, "Must Not Intersect (Line)", LIN_TRAM_PPTA_LINIA, "", "", ""),
            # No pot haver sobre posicions entre un mateix tram
            (TOPOLOGIA_LINIA, "Must Not Self-Overlap (Line)", LIN_TRAM_PPTA_LINIA, "", "", ""),
            # No pot haver interseccións entre un mateix tram
            (TOPOLOGIA_LINIA, "Must Not Self-Intersect (Line)", LIN_TRAM_PPTA_LINIA, "", "", "")
        )
        try:
            for in_topology, rule_type, in_featureclass, subtype, in_featureclass2, subtype2 in topology_rules_self_line:
                arcpy.AddRuleToTopology_management(in_topology, rule_type, in_featureclass,
                                                   subtype, in_featureclass2, subtype2)
            print
            "     Regles afegides a la topologia..."
        except:
            self.write_report(msg[3], "error")

        # Validar la topologia
        try:
            arcpy.ValidateTopology_management(TOPOLOGIA_LINIA)
            self.write_report(msg[0], "info")
        except:
            self.write_report(msg[4], "error")

    def check_topology_gdb(self):
        """Funció per a fer els controls topologics de la linia amb la base general"""
        msg = ("Topologia de la base creada i validada. Revisa els errors topològics",
               "No s'ha pogut afegir la línia a la base general", "No s'ha pogut crear una nova topologia",
               "No s'han pogut afegir les fc a la topologia", "No s'han pogut afegir les regles de topologia",
               "No s'ha pogut validar la topologia")

        # Variables d'entrada
        topo_nom = "CQlinia_Topology_base"
        cluster_tol = 0.001

        # Afegir la línia a la base general
        lin_tram_general = ESQUEMA_CQLINIA + "/Lin_Tram_Base"
        try:
            if arcpy.Exists(lin_tram_general):
                if arcpy.Exists(TOPOLOGIA_BASE):
                    arcpy.Delete_management(TOPOLOGIA_BASE)
                arcpy.Delete_management(lin_tram_general)
            arcpy.Merge_management([LIN_TRAM_PPTA, LIN_TRAM_PROPOSTA], lin_tram_general)
            print
            "     Linia afegida a la base general..."
        except arcpy.ExecuteError:
            self.write_report(msg[1], "error")

        # Llista amb les fc de la topologia
        fc_topologia_base = [FITA_G, lin_tram_general, PUNT]

        # Comprovar si existeig ja una topologia. Si existeix, la elimina
        try:
            if arcpy.Exists(TOPOLOGIA_BASE):
                arcpy.Delete_management(TOPOLOGIA_BASE)
            arcpy.CreateTopology_management(ESQUEMA_CQLINIA, topo_nom, cluster_tol)
            print("-- Topologia de la base creada. Iniciant controls topologics... ------------")
        except:
            self.write_report(msg[2], "error")

        # Afegir les fc a la topologia
        try:
            for fc in fc_topologia_base:
                arcpy.AddFeatureClassToTopology_management(TOPOLOGIA_BASE, fc)
            print("FC afegides a la topologia...")
        except:
            self.write_report(msg[3], "error")

        # Afegir regles de topologia
        topology_rules_line_gdb = (
            # Les linies han d'acabar sempre en una fita
            (TOPOLOGIA_BASE, "Endpoint Must Be Covered By (Line-Point)", lin_tram_general, "", FITA_G, ""),
            # No pot haver sobre posició entre linies
            (TOPOLOGIA_BASE, "Must Not Overlap (Line)", lin_tram_general, "", "", ""),
            # No pot haver intersecció entre linies
            (TOPOLOGIA_BASE, "Must Not Intersect (Line)", lin_tram_general, "", "", ""),
            # No pot haver sobre posicions entre una mateixa lina
            (TOPOLOGIA_BASE, "Must Not Self-Overlap (Line)", lin_tram_general, "", "", ""),
            # No pot haver interseccións entre una mateixa lina
            (TOPOLOGIA_BASE, "Must Not Self-Intersect (Line)", lin_tram_general, "", "", ""),
            # Les línies han d'acabar sempre amb una altra linia
            (TOPOLOGIA_BASE, "Must Not Have Dangles (Line)", lin_tram_general, "", "", ""),
            # Les fites de la linia han de coincidir amb les de la base
            (TOPOLOGIA_BASE, "Must Coincide With (Point-Point)", PUNT, "", FITA_G, "")
        )
        try:
            for in_topology, rule_type, in_featureclass, subtype, in_featureclass2, subtype2 in topology_rules_line_gdb:
                arcpy.AddRuleToTopology_management(in_topology, rule_type, in_featureclass,
                                                   subtype, in_featureclass2, subtype2)
            print
            "     Regles afegides a la topologia..."
        except:
            self.write_report(msg[4], "error")

        # Validar la topologia
        try:
            arcpy.ValidateTopology_management(TOPOLOGIA_BASE)
            self.write_report(msg[0], "info")
        except:
            self.write_report(msg[5], "error")

    def write_first_report(self):
        """
        Write first log's report
        """
        init_log_report = "ID Linia = {}:  Data i hora CQ: {}".format(self.line_id_txt, self.current_date)
        self.logger.info(init_log_report)

    def rm_temp(self):
        """

        :return:
        """
        gpkg = gdal.OpenEx(WORK_GPKG, gdal.OF_UPDATE, allowed_drivers=['GPKG'])
        for layer in TEMP_ENTITIES:
            layer_name = layer.split('.')[0]
            try:
                gpkg.ExecuteSQL(f'DROP TABLE {layer_name}')
            except:
                self.logger.error("Error esborrant arxius temporals")
                return

        self.logger.info('Arxius temporals esborrats')

    @staticmethod
    def open_mxd():
        """Open project mxd"""

        os.startfile(MXD_PATH)
