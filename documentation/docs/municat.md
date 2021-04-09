# Generador de carpetes pel Municat

L’aplicació Municat és una app destinada a extreure de la base de dades SIDM3 un seguit de línies i les seves corresponents fites per a posteriorment exportar aquestes geometries tant en format shapefile com CAD – concretament, dxf -. Aquest arxius es comprimeixen en un arxiu zip i es complementen amb la corresponent Memòria dels Treballs Topogràfics, en format PDF. El destinatari final d’aquesta informació són els Ajuntaments.

## Funcionament

El procés d'execució és senzill. En un primer pas, simplement s’ha d’obrir l’arxiu MTT.csv i introduir en ordre els camps ID Linia, ID Sessio, Data i Nº de memòria, tot en una única línia i separat només per comes `,`. Es pot fer simplement amb Excel, tot i que és més fàcil de fer amb Notepad++. Un cop fet això ja es pot executar el procés i, quan s'indiqui a pantalla que les carpetes s'han generat correctament, ja es poden gestionar les dades, les quals s'han exportar a la corresponent carpeta de sortides.

