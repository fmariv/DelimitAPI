import os
from django.core.management.base import BaseCommand
import geopandas as gpd
from qa_line.config import *


class Command(BaseCommand):
    """Update the local database with data from the PostGIS"""

    def handle(self, *args, **options):
        """Update local database"""
        # Export layers to the updating environment
        cmd = f'''ogr2ogr -f GPKG {UPDATING_GPKG} PG:"host={host} user={user} dbname={dbname} password={pwd} tables=sidm3.v_fita_mem,sidm3.v_tram_linia_mem,sidm3.v_fita_rep,sidm3.v_tram_linia_rep"'''
        os.system(cmd)
        # Copy layers to the local working geopackage
        # Official
        # Points
        point_mem_gdf = gpd.read_file(UPDATING_GPKG, layer='sidm3.v_fita_mem')
        point_mem_gdf.to_file(WORK_GPKG, layer='fita_mem', driver="GPKG")
        # Tram line
        tram_mem_gdf = gpd.read_file(UPDATING_GPKG, layer='sidm3.v_tram_linia_mem')
        tram_mem_gdf.to_file(WORK_GPKG, layer='tram_linia_mem', driver="GPKG")
        # Non official
        # Points
        point_rep_gdf = gpd.read_file(UPDATING_GPKG, layer='sidm3.v_fita_rep')
        point_rep_gdf.to_file(WORK_GPKG, layer='fita_rep', driver="GPKG")
        # Tram line
        tram_rep_gdf = gpd.read_file(UPDATING_GPKG, layer='sidm3.v_tram_linia_rep')
        tram_rep_gdf.to_file(WORK_GPKG, layer='tram_linia_rep', driver="GPKG")

        print("Geopackage local actualitzat")
