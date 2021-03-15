import os
from django.core.management.base import BaseCommand
import geopandas as gpd
from qa_line.config import *


class Command(BaseCommand):
    """Update the local database with data from the PostGIS"""

    def handle(self, *args, **options):
        """Update local database"""
        # Export layers to the updating environment
        cmd = f'''ogr2ogr -f GPKG {UPDATING_GPKG} PG:"host={host} user={user} dbname={dbname} password={pwd} tables=sidm3.v_fita_mem,sidm3.v_tram_linia_mem"'''
        os.system(cmd)
        # Copy layers to the local working geopackage
        # Points
        point_gdf = gpd.read_file(UPDATING_GPKG, layer='sidm3.v_fita_mem')
        point_gdf.to_file(WORK_GPKG, layer='fita_mem', driver="GPKG")
        # Tram line
        point_gdf = gpd.read_file(UPDATING_GPKG, layer='sidm3.v_tram_linia_mem')
        point_gdf.to_file(WORK_GPKG, layer='tram_linia_mem', driver="GPKG")

        print("Geopackage local actualitzat")
