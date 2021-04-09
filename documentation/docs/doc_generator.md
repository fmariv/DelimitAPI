# Generador de documents pels ajuntaments

L'aplicació Generador de documents és una app que té per objectiu generar de manera automàtica
les cartes que s'han d'enviar als ajuntaments quan se'ls obre un nou expedient, ja sigui de
delimitació o de replantejament. D'aquesta manera, i prèvia l'extracció de les dades corresponents,
les cartes es generen amb les corresponents dades de cada ajuntament i per la seva línia de terme,
com per exemple l'ID de la línia, nom i cognoms de l'alcalde o alcaldessa, data de les Operacions de Delimitació, etc. 
Així, els documents es generen primer en format `docx` de Microsoft Word i desprès en format `pdf`, 
preparats per ser enviats als ajuntaments.

## Funcionament

En primer lloc, s'ha d'extreure la informació dels ajuntaments necessària per poder omplir 
posteriorment les cartes. Així, aquest pas s'executa amb el botó `Extreure informació del Municat`,
i consisteix precisament en això. Per que l'aplicació sàpigui de quines línies i ajuntaments en concret
ha d'extreure la informació s'haurà d'editar l'arxiu `llistats_id_linia`, ubicat a `doc_generator\info_municat\data`, 
i indicar l'ID linia i l'enllaç de OneDrive que s'envia als ajuntaments amb l'informació associada,
tot en una mateixa línia. Un cop fet això es pot executar el procés, el qual dona com a resultat un arxiu
en format `xlsx` de Microsoft Excel anomenat `info_municat` i que està ubicat a `doc_generator\info_municat\output`.

En aquest moment ja es poden generar les cartes en format `docx`, escollint a la mateixa pantalla de l'aplicació
si les cartes a generar son d'un expedient de replantejament o d'un expedient de delimitació. Si es tracta d'un expedient
de replantejament no cal fer res, de manera que es poden generar les cartes directament. No obstant, si es tracta
d'un expedient de delimitació no és tant senzill, i s'han de fer certes edicions al document `info_municat` generat
prèviament. Aquestes edicions consisteixen, bàsicament, en omplir tres columnes de l'arxiu d'Excel: 

   - DATA-OD: s'indica la data de les operacions de delimitació. Ha de ser en format dd/mm/aaaa.
   - HORA-OD: s'indica l'hora de les operacions de delimitació. Ha de ser en format HH:MM.
   - LOCAL: s'indica si l'ajuntament d'aquell registre concret és l'ens local o no. Ha de ser en format 'S' si ho és o 'N'
si no ho és.
  
Un cop dutes a termes aquestes edicions, ja es poden generar les cartes per aquests expedients de delimitació.

Les cartes es generen en un primer pas en format `docx`, a la carpeta `doc_generator\cartes\[delimitacio-replantejament]\output\word`.
Un cop generades i revisat que totes siguin correctes i/o fetes les edicions corresponents, es pot continuar al següent pas,
que és transformar-les de format `docx` a `pdf`. Les cartes resultants es troben a la carpeta `doc_generator\cartes\[delimitacio-replantejament]\output\pdf`.
Per acabar, i un cop enviades les cartes o copiades a una altra carpeta, es pot executar el botó `Esborrar cartes` per buidar les carpetes
de sortides.