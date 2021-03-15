from django.core.management.base import BaseCommand
from osgeo import gdal
from qa_line.config import *
from fiona import listlayers


class Command(BaseCommand):
    """Clear and remove temp layers in the geopackage database"""

    def handle(self, *args, **options):
        """Remove all of the temporal files from the workspace"""
        gpkg = gdal.OpenEx(WORK_GPKG, gdal.OF_UPDATE, allowed_drivers=['GPKG'])
        for layer_name in listlayers(WORK_GPKG):
            if layer_name not in PERSISTENT_ENTITIES:
                gpkg.ExecuteSQL(f'DROP TABLE {layer_name}')

        self.stdout.write('Arxius temporals esborrats')
