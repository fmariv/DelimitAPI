# -*- coding: utf-8 -*-

# ----------------------------------------------------------
# TERRITORIAL DELIMITATION TOOLS (ICGC)
# Authors: Cesc Masdeu & Fran Martin
# Version: 3.1
# Date: 20201026
# Version ArcGIS: 10.1
# Version Python: 2.7.2
# ----------------------------------------------------------


"""
Quality check and control of a line ready to upload to the database
"""

# Standard library imports
import os
import os.path as path
import decimal
from datetime import datetime
import logging
import numpy
import re

# Third party imports
from django.http import JsonResponse
from django.views import View
import fiona

# Local imports
from CQline.config import *


class CheckQualityLine(View):
    """
    Class for checking a line's geometry and attributes quality previous to upload it into the database
    """

    def get(self, request, line_id):
        """
        Main entry point. Here is where the magic is done. This method is called when someone wants to init the process of quality
        checking and is supposed to prepare the workspace, prepare the line and check it's geometry and attributes
        """
        print()
        print("Procés per dur a terme el control de qualitat d'una línia")
        print("=========================================================")

        # Set class parameters
        self.set_config(line_id)

        # Check if line ID is valid
        if line_id is None:
            return

        # Write first log message
        self.write_first_report()

        '''
        # Esborrar arxius temporals
        self.del_temp(False)

        # Copiar les capes i taules de Docdelim de la linia a CQlinia.gdb
        self.copy_line_2_cqlinia()

        # Comprovar si l'IDLINIA existeix a FitaG i Lin_Tram_Proposta
        self.check_id_linia(self.id_linia_num)

        # Crear llista amb les fites que son Proposta Final
        self.llista_punts_ppta = self.ppf.totes(PUNT_PROPOSTA)

        # Comprovar l'estructura i contingut de la carpeta
        self.check_directory()

        # Comprovar que l'estructura de camps de Lin_Tram_Ppta és correcte
        self.check_fields_structure()

        # Comprovar que els camps de Lin_Tram_Ppta estan correctament emplenats
        self.check_fields_fill()

        # Donar informació sobre els vertex de les linies
        self.info_vertex_linia()

        # Comprovar la decimetrització de les fites
        self.decim_fites()

        # Comprovar les fites Proposta Final
        self.check_ppf()

        # Comprovar que les fites auxiliars tinguin correctament indicat el camp ID_FITA
        self.check_aux_id()

        # Comprovar diferents aspectes de les fites trobades
        self.check_fites_trobades()

        # Comprovar les fites 3 termes
        self.check_3termes()

        # Comprovar la correspondència entre taules i capes
        self.check_corresp_fites_taules()

        # Fer els controls topològics
        self.check_topology()
        '''

        return JsonResponse({'data': '-- Linia {} checkejada --\n'.format(line_id)})

    def set_config(self, line_id):
        """

        :param line_id:
        :return:
        """
        self.line_id = line_id
        # Convert line ID from integer to string nnnn
        self.line_id_txt = self.line_id_2_txt(line_id)
        # Get current date and time
        self.current_date = datetime.now().strftime("%Y%m%d-%H%M")
        # Configure logger
        self.logger = logging.getLogger()
        self.set_logging_config()
        self.set_logging_config()

    def set_logging_config(self):
        """

        :return:
        """
        # Logging level
        self.logger.setLevel(logging.INFO)
        # Message format
        log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        # Log filename and path
        log_name = f"ReportCQ_{self.line_id_txt}_{self.current_date}.txt"
        # log_path = os.path.join(LINES_DIR, str(self.line_id), WORK_REC_DIR, log_name)
        log_path = os.path.join(r'C:\Users\fmart\Documents\Work\ICGC\DelimitAPI\logs', log_name)
        file_handler = logging.FileHandler(filename=log_path, mode='w')
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)

    @staticmethod
    def line_id_2_txt(line_id_int):
        """
        Convert line id (integer) to string nnnn
        :param line_id_int -> <int> ID de línia introduit en format número
        :return: line_id_txt -> <string> ID de la línia introduit en format text
        """
        line_id_str = str(line_id_int)
        if len(line_id_str) == 1:
            line_id_txt = "000" + line_id_str
        elif len(line_id_str) == 2:
            line_id_txt = "00" + line_id_str
        elif len(line_id_str) == 3:
            line_id_txt = "0" + line_id_str
        else:
            line_id_txt = line_id_str

        return line_id_txt

    def check_directory(self, line_id):
        """Funció per comprovar que l'estructura i contingut de la carpeta són correctes"""
        msg = ("Estructura de directoris OK", "No existeix DocDelim dins el directori de la linia",
               "No existeix la linia al directori YYYY")
        # TODO Fix check directory
        # subdirectoris en funció de l'idLinia:
        line_folder = os.path.join(DIR_ENTRADA, str(line_id))
        doc_delim = os.path.join(line_folder, r"DocDelim")
        tree_valid = False

        if path.exists(line_folder):  # Check if the line folder exists at the loading folder
            if path.exists(doc_delim):  # Check the DocDelim folder exists
                for subDir in SUB_DIR_LIST:  # Check if subdirs exist
                    if subDir in os.listdir(doc_delim):
                        tree_valid = True
                    else:
                        self.write_report("No existeix {}".format(subDir), "error")
            else:
                self.write_report(msg[1], "error")
        else:
            self.write_report(msg[2], "error")

        if tree_valid:
            self.write_report(msg[0], "ok")

    def copy_line_2_cqlinia(self):
        """Funció per copiar les capes i taules de Docdelim de la linia de YYYY a CQlinia.gdb"""
        msg = ("Capes i taules de {} copiades a CQlinia.gdb".format(self.id_linia_num),
               "No existeixen les capes i taules necessaries a DocDelim")

        # subdirectoris en funció de l'idLinia:
        linia_folder = DIR_ENTRADA + "\\" + str(self.id_linia_num)
        doc_delim = linia_folder + r"\DocDelim"
        print
        doc_delim

        try:  # Comprovar que existeixen les capes i taules necessàries per pujar a SIDM2
            for fc in FC_LIST:
                if arcpy.Exists(doc_delim + "\\" + SUB_DIR_LIST[0] + "\\" + fc):  # comprovar capes de "Cartografia"
                    try:
                        arcpy.FeatureClassToGeodatabase_conversion(doc_delim + "\\" + SUB_DIR_LIST[0] + "\\" + fc,
                                                                   ESQUEMA_CQLINIA)
                    except arcpy.ExecuteError:
                        self.write_report("No s'ha pogut copiar {}".format(fc), 'error')
                else:
                    self.write_report("No existeix {}".format(fc), 'error')

            for dbf in TABLE_LIST:
                if arcpy.Exists(doc_delim + "\\" + SUB_DIR_LIST[3] + "\\" + dbf):  # comprovar taules de "Cartografia"
                    try:
                        arcpy.TableToGeodatabase_conversion(doc_delim + "\\" + SUB_DIR_LIST[3] + "\\" + dbf, WORK)
                    except arcpy.ExecuteError:
                        self.write_report("No s'ha pogut copiar {}".format(dbf), 'error')
                else:
                    self.write_report("No existeix {}".format(dbf), 'error')
            self.write_report(msg[0], "ok")
        except RuntimeError:
            self.write_report(msg[1], "error")

    # -- FUNCIONS QUE OBTENEN INFORMACIÓ DE CAPES I TAULES ----------------------------

    @staticmethod
    def get_info_fc(fc, schema_path):
        """
        Funció per a obtenir informació de la capa Punt
        :param fc -> <shapefile> feature class de la qual es vol obtenir informació
        :param schema_path -> <string> ruta on s'ubica la feature class de la qual es vol obtenir informacó
        :return: arr -> <numpy array> array amb informació de la feature class introduida
        """
        camps_punt = ("ID_PUNT", "SHAPE@XY", "ETIQUETA", "FOTOS", "CONTACTE")
        camps_punt_fit = ("ID_PUNT", "ID_FITA", "TROBADA", "AUX")
        camps_p_proposta = ("ID_PUNT", "ESFITA", "PFF")

        if fc == "Punt":
            camps = camps_punt
        elif fc == "PUNT_FIT":
            camps = camps_punt_fit
        else:
            camps = camps_p_proposta

        arr = arcpy.da.FeatureClassToNumPyArray(schema_path + "\\" + fc, camps)
        print
        arr
        return arr

    def check_id_linia(self, id_linia):
        """
        Funció per a comprovar si l'IdLinia existeix a FitaG i Lin_Tram_Proposta
        :param id_linia -> ID de la línia de la qual es vol comprovar si existeix a FitaG i Lin_Tram_Proposta
        """
        msg = ("L'IdLinia introduït no està repetit en SIDM2", "L'IdLinia introduït està en FitaG i Lin_Tram_Proposta",
               "L'IdLinia introduït està FitaG pero no en Lin_Tram_Proposta",
               "L'IdLinia introduït no està FitaG pero si en Lin_Tram_Proposta")
        # Crear arrays amb el total de IdLinia que hi ha a FitaG i LinTramProposta
        llista_linia_lin_tram = []
        llista_linia_fita_g = []

        with arcpy.da.SearchCursor(LIN_TRAM_PROPOSTA, "ID_Linia") as cursor:
            for row in cursor:
                llista_linia_lin_tram.append(row[0])

        with arcpy.da.SearchCursor(FITA_G, "ID_LINIA") as cursor:
            for row in cursor:
                llista_linia_fita_g.append(row[0])

        # Comprovar si IdLinia està en Fita_G i LinTramProposta
        if id_linia in llista_linia_fita_g and id_linia in llista_linia_lin_tram:
            self.write_report(msg[1], "error")
        elif id_linia in llista_linia_fita_g and id_linia not in llista_linia_lin_tram:
            self.write_report(msg[2], "error")
        elif id_linia not in llista_linia_fita_g and id_linia in llista_linia_lin_tram:
            self.write_report(msg[3], "error")
        elif id_linia not in llista_linia_fita_g and id_linia not in llista_linia_lin_tram:
            self.write_report(msg[0], "ok")

    def check_fields_structure(self):
        """Comprovar que l'estructura de camps de la capa Lin_TramPpta és correcte"""
        true_fields = ('Shape', 'ID_LINIA', 'ID', 'DATA', 'COMENTARI', 'P1', 'P2', 'P3', 'P4', 'PF',
                       'ID_FITA1', 'ID_FITA2')
        msg = ("L'estructura de camps de Lin_TramPpta es correcte",
               "L'estructura de camps de Lin_TramPpta no es correcte")

        field_match = 0
        fields = arcpy.ListFields(LIN_TRAM_PPTA)
        for field in fields:
            if field.name in true_fields:
                field_match += 1

        if field_match == len(true_fields):
            self.write_report(msg[0], 'ok')
        else:
            self.write_report(msg[1], 'error')

    def check_fields_fill(self):
        """Comprovar si la capa Lin_TramPpta té els camps correctament emplenats"""
        error = False
        msg = ('Camps de Lin_TramPpta emplenats correctament',
               'Algun dels camps ID_FITA de Lin_Tram_Ppta no estan correctament emplenats')

        # Comprovar camp ID_LINIA
        with arcpy.da.SearchCursor(LIN_TRAM_PPTA, ['ID_LINIA', 'ID_FITA1', 'ID_FITA2']) as cur:
            for id_linia, id_fita1, id_fita2 in cur:
                if id_linia != self.id_linia_num:
                    error = True
                    self.write_report('El camp ID_LINIA de Lin_Tram_Ppta es incorrecte i te com a valor "{}"'.format(
                        id_linia), 'error')
                if len(id_fita1) == 1 or len(id_fita2) == 1:
                    if not error:
                        error = True
                    self.write_report(msg[1], 'error')
        if not error:
            self.write_report(msg[0], 'ok')

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

    def check_aux_id(self):
        """Funció per a comprovar que les fites auxiliars tenen correctament indicat l'ID de la seva fita real"""
        id_fita_real_arr = arcpy.da.FeatureClassToNumPyArray(PUNT_FIT, 'ID_FITA', where_clause="AUX = '0'")
        id_fita_aux_arr = arcpy.da.FeatureClassToNumPyArray(PUNT_FIT, 'ID_FITA', where_clause="AUX = '1'")
        for id_fita in id_fita_aux_arr:
            if id_fita not in id_fita_real_arr:
                id_fita_num = id_fita[0]
                self.write_report(
                    "La fita auxiliar {} no te correctament indicat l'ID de la fita real".format(id_fita_num),
                    'error')

    def check_ppf(self):
        """Funció per a fer les comprovacions de les fites de proposta final a la taula P_Proposta"""
        # Informar de quantes fites hi ha informades a la taula pProposta.
        # També: informar de quantes són PF )i si són o no auxiliars) i quantes són Propostes no finals
        val_ok = 0
        fites_proposta = 0
        fites_auxiliars = 0
        fites_no_finals = 0

        with arcpy.da.SearchCursor(PUNT_PROPOSTA, ("PFF", "ESFITA")) as cursor:
            for row in cursor:
                if row[0] == 1 and row[1] == 1:
                    fites_proposta += 1
                elif row[0] == 1 and row[1] == 0:
                    fites_auxiliars += 1
                elif row[0] == 0:
                    fites_no_finals += 1
        info = " Informació de les fites \n   => Fites PFF reals: " + str(
            fites_proposta) + "\n   => Fites PFF auxiliars: " + str(
            fites_auxiliars) + "\n   => Fites no finals (PFn): " + str(fites_no_finals)
        self.write_report(info, "info")

        # Comprovar que l'ORDPF de les fites no té un valor nul
        with arcpy.da.SearchCursor(PUNT_PROPOSTA, ("ID_PUNT", "ORDPF")) as cursor:
            for row in cursor:
                if row[1] is None:
                    self.write_report("L'ORDPF del punt {0} és nul".format(row[0]), "error")
                else:
                    val_ok += 1

        # Comprovar que si PFF = 1 i ORDPF = 0 => ESFITA = 0
        with arcpy.da.SearchCursor(PUNT_PROPOSTA, ("ID_PUNT", "PFF", "ORDPF", "ESFITA")) as cursor:
            for row in cursor:
                if row[1] == 1 and row[2] == 0:
                    if row[3] != 0:
                        self.write_report("El punt {0} té error de codificació a la Proposta".format(row[0]),
                                          "error")
                else:
                    val_ok += 1
        print
        val_ok
        if val_ok == 2:
            self.write_report("Estructura de p_proposta OK", "ok")

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

    def decim_fites(self):
        """Funció per a comprovar la decimetrització de les fites"""
        val_ok2 = 0

        array_punt = self.get_info_fc("Punt", ESQUEMA_CQLINIA)

        for row in array_punt:
            punt_id = row[0]
            if punt_id not in self.llista_punts_ppta:
                where = numpy.where(array_punt == row)
                where_array = where[0]
                index = where_array[0]
                array_punt = numpy.delete(array_punt, index)

        for idPunt, coord, etiq, foto, contacte in array_punt:
            e = "Punt {} no decimetritzat ({},{})".format(idPunt, coord[0], coord[1])
            # Get coordinates
            coord_x = str(coord[0])
            coord_y = str(coord[1])
            # Get decimals
            coord_x_decim = decimal.Decimal(coord_x).as_tuple().exponent
            coord_y_decim = decimal.Decimal(coord_y).as_tuple().exponent
            # Aquí s'ha de modificar el número de decimals sobre els quals es volen capar les coordenades
            # https://stackoverflow.com/questions/6189956/easy-way-of-finding-decimal-places
            if coord_x_decim != -1 or coord_y_decim != -1:
                self.write_report(e, "error")
                val_ok2 = 1

        if val_ok2 == 0:
            self.write_report("Decimals fites OK", "ok")

    def info_vertex_linia(self):
        """Funció per a obtenir informació sobre els vertex de la linia"""
        self.write_report('Vèrtex de la linia:', "info")

        # Enter for loop for each feature
        for row in arcpy.da.SearchCursor(LIN_TRAM_PPTA, ["OBJECTID", "SHAPE@"]):
            partnum = 0
            multipart = ""
            try:
                # Step through each part of the feature
                for part in row[1]:
                    # Step through each vertex in the feature
                    vertex = 0
                    for pnt in part:
                        if pnt:
                            vertex += 1
                        else:
                            # If pnt is None, this represents an interior ring
                            print("Interior Ring:")

                    if partnum > 0:
                        multipart = "Error! (multipart)"
                    partnum += 1
            except TypeError:
                e = "Un dels trams no té geometria. Si us plau, revisa'l."
                self.write_report(e, 'error')
                exit()

            # Print info
            missatge_sub_info = "Tram OBJECTID = {}:  Parts({})  Vèrtex({})  {}".format(row[0], partnum, vertex,
                                                                                        multipart)
            # Afegir un altre salt de línia per a diferenciar bé els trams al report...
            missatge_sub_info = missatge_sub_info + "\n"
            self.write_report(missatge_sub_info, "subinfo")

    def write_first_report(self):
        """
        Write first log's report
        """
        init_log_report = "ID Linia = {}:  Data i hora CQ: {}".format(self.line_id_txt, self.current_date)
        self.logger.info(init_log_report)

    def del_temp(self, manual=True):
        """Funció per a esborrar els temporals dins la CQlinia.gdb, si existeixen
        :param manual -> <bool> Paràmetre per a indicar com es llença la funció. Veure explicació a sota.
        """

        '''
        El paràmetre 'manual' indica si la funció del_temp es llença en el moment de checkejar una línia,
        on s'esborren tots els temporals per a preparar l'espai de treball, o si per contra es llença 
        manualment prement el botó. Aquest fet té implicacions bàsicament per reportar la resolució 
        del procés, de manera que indica si s'ha de fer el report a un log (quan es checkeja una línia)
        o només s'ha de fer el report a la caixa de text de sortida de l'aplicatiu. Permet evitar que, en aquest
        últim cas, l'aplicatiu no detecti que no s'ha introduït un ID de línia
        '''

        msg = ("S'han esborrat els arxius temporals", "No s'han pogut esborrar els arxius temporals")

        if not manual:
            id_linia_intro_exists = self.get_id_linia_intro()
        try:
            # Comprovar si hi ha topologia a l'esquema principal que pugui bloquejar eliminar els arxius existents
            if arcpy.Exists(TOPOLOGIA_BASE):
                arcpy.Delete_management(TOPOLOGIA_BASE)
            # Comprovar si hi ha topologia a l'esquema de la línia que pugui bloquejar eliminar els arxius existents
            if arcpy.Exists(TOPOLOGIA_LINIA):
                arcpy.Delete_management(TOPOLOGIA_LINIA)
            # Eliminar temporals a l'espai de treball
            if path.exists(WORK):
                for dirpath, dirnames, datatypes in arcpy.da.Walk(WORK):
                    for datatype in datatypes:
                        if datatype != "FITA_G_temp" and datatype != "LIN_TRAM_PROPOSTA_temp":
                            arcpy.Delete_management(os.path.join(dirpath, datatype))
                self.app_writer.report(msg[0], 'ok')
        except arcpy.ExecuteError:
            if not manual:
                if id_linia_intro_exists is None:
                    self.app_writer.report(msg[1], 'error')
                else:
                    self.write_report(msg[1], 'error')
                    exit()
            else:
                self.app_writer.report(msg[1], 'error')

    @staticmethod
    def open_mxd():
        """Open project mxd"""

        os.startfile(MXD_PATH)
