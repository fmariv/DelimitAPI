# -*- coding: utf-8 -*-

# ----------------------------------------------------------
# TERRITORIAL DELIMITATION TOOLS (ICGC)
# Authors: Fran Martin
# Version: 1
# Date: 20210315
# Version Python: 3.7
# ----------------------------------------------------------

"""
Common functions
"""


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
