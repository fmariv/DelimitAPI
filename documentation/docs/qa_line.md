# Control de qualitat d'una línia

L’aplicació CQ linia és una app destinada a fer un control de la qualitat i 
validesa de les línies i fites que estan preparades per a ser pujades a SIDM3, amb 
l’objectiu tant de prevenir errors en el moment de carregar les línies a la base de
dades com d’evitar la presència elements nocius a la mateixa que puguin malmetre la 
resta de dades.

## Funcionament

Quasi bé tot el procés de control de qualitat està automatitzat i es controla amb un únic botó. D’aquesta manera, simplement s’ha d’introduir l’ID de la línia que es vol controlar, i començarà el procés. És imprescindible que per dur a terme el control de qualitat la carpeta de la 
línia estigui al NAS de l'ADT, a `linies_per_carregar`.

Un cop finalitzat el procés de control de qualitat, s’imprimirà a la finestra un report amb tota l’informació relativa al control de la línia preparada (per a veure quins aspectes es controlen, veure apartat posterior). Més encara, l’aplicatiu crea i desa un arxiu de format txt que conté la totalitat del report que imprimeix a pantalla. Aquest arxiu es guarda a la carpeta de treball del directori de reconeixements, tal i com es mostra a l’exemple següent:
`Linies\[ID_Linia]\3_Reconeixements\2_Carp_treball`.

L’últim pas a dur a terme un cop comprobat el report de l’aplicatiu és obrir el projecte de QGIS de control de qualitat, per tal de veure les dades i de comprovar els possibles errors alfanumèrics i topològics que es puguin donar tant dins de la mateixa línia com entre aquesta i les línies ja presents a la base de dades.
L'arxiu `qgs` amb el projecte de QGIS es troba a `Programari_i_instruccions\APPs_Delimitacio\DelimitAPI\cq_linia`.



## Aspectes a controlar
### General

Els aspectes que controla l’aplicatiu són els que es contemplen a continuació:

-	Comprovar si existeix ja una línia carregada a SIDM3.
-	Comprovar la validesa de la capa Lin_Tram_Ppta. 
     - Comprovar estructura de camps.
     - Comprovar informació continguda als camps.
-	Comprovació de tram de línia:
     - Número de trams correcte. Informar del número de trams.
     - Comprovar que no hi ha trams multipart.
     - Comprovar que no hi ha trams que es sobreposin, que tinguin final a una fita, que no estiguin partits, etc.
-	Comprovar decimetrització:
     - Comprovar que les fites tenen 1 decimal (o 0). 
     - Comprovar que els vèrtex finals de la línia tenen 1 decimal.
-	Comprovacions de Fites Proposta Final (taula p_proposta):
     - Informar de quantes fites Proposta final hi ha i quantes d’auxiliat:
     -	El camp ORDPF no pot ser nul.
     - 	Controlar les fites auxiliars informades correctament.
-	Comprovació Fites trobades:
     -	Comprovar que si és una fita trobada ha de tenir fotografia informada.
     - 	Comprovar que la fotografia informada té el mateix nom que el fitxer JPG.
     - 	Comprovar que una fita amb cota és fita trobada. 
-	Comprovació Fites 3 termes:
     -	Si és F3T ha de tenir text al camp CONTACTE
     -	Ha de coincidir amb la posició de les F3T de les altres línies que hi convergeixen.
-	Correspondència entre capes i taules segons ID_PUNT:
     -	Tots els ID_PUNT de P_proposta han d’estar a la capa PUNT.
     -	Tots els ID_PUNT de PUNT_FIT han d’estar a la capa PUNT.
    
### Controls topològics

Amb l’objectiu d’evitar possibles errors topològics a la base de dades es desenvolupen dos controls topològics diferents. Així, mentre que per un costat es dur a terme un control topològic únicament per a les geometries de la línia preparada, per l’altre costat es dur a terme un control entre la geometria de la línia preparada i la resta de geometries contingudes a SIDM2. Les normes topològiques amb les quals es duen a terme els controls són les que es contemplen a continuació.

- Línia controlada amb les geometries de SIDM3:
    -	Que les línies acabin sempre en una fita. 
    -	Que les línies acabin sempre amb una altra línia. 
    -	Que no hi hagi intersecció entre línies. 
    -	Que no hi hagi sobre posició entre línies.
    
- Línia controlada únicament amb les seves pròpies geometries:
    -	Que els trams acabin sempre en una fita. 
    - 	Una fita que no estigui sobre una tram, només pot ser auxiliar.
    -	Que no hi hagi intersecció entre trams ni amb un mateix tram. 
    -	Que no hi hagi sobre posició entre trams ni amb un mateix tram. 

