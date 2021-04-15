# Per desenvolupadors

Aquesta pàgina està destinada a aquells desenvolupadors que tinguin la necessitat d'editar,
millorar o ampliar el codi base de l'aplicació, ja sigui per l'aparició d'errors o la simple
necessitat d'afegir més funcionalitats. Així doncs, s'intentarà explicar de la manera més fàcil
possible l'estructura i funcionament de la DelimitAPI.

## Documentació base de tercers

El projecte es basa en Django, un framework de desenvolupament web per Python. Per veure la documentació,
anar [aquí](https://www.djangoproject.com/).

Aquesta documentació es basa en Mkdocs, un generador de llocs webs estàtics destinats a 
servir documentació. Per veure la seva, anar [aquí](https://www.mkdocs.org/).

L'entorn de Python de l'aplicatiu està fet amb Conda i s'anomena `DelimitAPI`. Per veure la documentació
de Conda, anar [aquí](https://docs.conda.io/en/latest//).

## Servidor

L'aplicatiu es troba allotjat a la màquina `Darling`, la qual fa de servidor. Així, aquesta mateixa
màquina s'encarrega de servir 3 components diferents:
 - Mitjançant l'aplicació MAMP, serveix els estils de l'aplicatiu al port `:80`.
 - Mitjançant una finestra d'Anaconda Prompt, serveix l'aplicatiu DelimitAPI pròpiament dit al port `:8000`.
 - Mitjançant una altra finestra d'Anaconda Prompt, serveix la documentació al port `:8888`.

L'aplicació és accesible desde altres màquines amb l'enllaç `darling.icgc.local:8000`. Per servir-la desde Darling, 
simplement s'ha d'iniciar el MAMP i executar l'arxiu `activar-delimitapi.bat` ubicat a `Soft_devel`.

## Estructura del projecte

El codi de l'aplicatiu es troba a `Soft_devel\DelimitAPI`. El projecte es divideix en aplicacions, on cada aplicació
té el seu propi codi base. Totes les rutes i informació sensible es guarden en arxius `config.py` que no es
guarden al Git, per la qual cosa no s'emmagatzemen a cap lloc ni es mostren a cap repositori de codi.

Actualment hi ha 3 aplicacions al projecte:
 - qa_line: per dur a terme els controls de qualitat de les línies prèvia càrrega a SIDM3.
 - doc_generator: per generar automàticament diferents tipus de documents.
 - municat_generator: per generar automàticament les carpetes de les línies pel Municat.

### Activar l'entorn de treball

Per activar l'entorn de treball del projecte, amb totes els paquets instal·lats, simplement s'ha
d'obrir l'aplicació `Anaconda prompt` i escriure `conda activate DelimitAPI`. Quan a la finestra surti
al principi de la línia de comandes `(DelimitAPI)` voldrà dir que s'ha activat.

## Funcionament

El funcionament bàsic ce Django és el següent: als arxius `urls.py` s'informen un seguit d'
urls on, per cadasquna, s'indica quina funció es llença quan un usuari vol accedir a aquella url.
Aquestes funcions s'emmagatzemen als arxius `views.py` de cada aplicació del projecte, que són els arxius que contenen el
codi de la lógica de l'aplicació. Per tant, si hi ha cap error o es vol fer cap millora, s'ha d'editar aquest arxiu.

Com a nota d'ajuda, és important afegir el següent: quan a l'arxiu `urls.py` es crida
a una funció acabada en `.as_view()` vol dir que realment no es crida a una funció com a tal,
si no a l'objecte d'una classe. En aquest cas, a l'arxiu `views.py` s'haurà de buscar la classe
i la funció `get`, que és on estarà tot el codi de la lógica d'aquesta classe. Si per contrari la funció no
acaba en `.as_view()`, es tracta d'una simple funció.

> Per exemple, a l'arxiu `urls.py` de l'aplicació doc_generator hi ha una url que crida al mètode `MunicatDataExtractor.as_view()`. En
aquest cas, el que s'ha de buscar a l'arxiu `views` és la funció `get` de la classe `MunicatDataExtractor`. Per l'altre costat,
existeix una altre url que crida al mètode `generate_letters_doc`. En aquest altre cas, el que 
s'ha de buscar és la funció `generate_letters_doc()`.

A la vegada, els arxius `html` de l'aplicació es troben a les respectives carpetes
anomenades templates. 

### Comandaments

Hi ha un total de dos comandaments que es poden llençar desde l'entorn de l'aplicatiu amb diferents objectius.
El primer que s'ha de fer, per tal de poder llençar-los correctament, és anar al directori de l'aplicatiu,
`Programari_i_instruccions\APPs_Delimitacio\DelimitAPI`, amb una finestra d'Anaconda Prompt. Un cop aquí, hi ha 
dos comandaments possibles:
- `python manage.py updatedb` té per lógica actualitzar el geopackage local de treball amb les dades de SIDM3.
- `python manage.py cleardb` té per lógica netejear i esborrar temporals del geopackage local de treball.