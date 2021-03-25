# +---------------------+
# | VARIABLES I ENTORNS |
# +---------------------+

import os.path as path

# -----------------------------------------------------------------------------------
# ESTABLIR ENTORN DE TREBALL

WORK_GPKG = r'../DelimitAPI/db/SIDM3.gpkg'

# ESTABLIR PATHS
#MUNICAT_GENERATOR_WORK = r'V:\Programari_i_instruccions\APPs_Delimitacio\DelimitAPI\'
MUNICAT_GENERATOR_WORK = r'C:\Users\fmart\Documents\Work\ICGC\DelimitAPI'
OUTPUT = path.join(MUNICAT_GENERATOR_WORK, 'municat')
FOLDERS =  path.join(OUTPUT, 'sortides')
MTT = path.join(OUTPUT, 'MTT.csv')

# CAPES I TAULES
TEMP_ENTITIES = ['Fita_mem_municat_temp', 'Line_tram_mem_municat_temp']

# -----------------------------------------------------------------------------------
# ESTABLIR PATHS

# LINIES
#LINES_DIR = r'V:\MapaMunicipal\Linies'
LINES_DIR = r'C:\Users\fmart\Documents\Work\ICGC\DelimitAPI\Test\Linies'

# PATH DELS PDF
# ED50
PDF_ED50 = r'0_ED50\4_MemoriesTT\1_MTT_pdf'
# ETRS89
PDF_ETRS89 = r'4_MemoriesTT\1_MTT_pdf'

# LOG
LOG_DIR = path.join(OUTPUT, 'logs')
