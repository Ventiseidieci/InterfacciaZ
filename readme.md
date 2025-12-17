# Conic Studio (interfacciaZ)

Il seguente tool, basato sulla ricerca eseguita dal canale [CNC Kitchen](https://github.com/RotBotSlicer/Transform), consente di eseguire uno "slicing conico" dei corpi modellati in 3D. Questa tipologia di slicing consente di stampare sbalzi importanti senza utilizzare neccesariamente supporti. Questa strategia permette di risparmiare tempo di stampa e materiale impiegato.

<img src= "https://github.com/Ventiseidieci/InterfacciaZ/blob/main/images/predeformation.png" width="30%" height="30%"><img src= "https://github.com/Ventiseidieci/InterfacciaZ/blob/main/images/backtransformation.png" width="30%" height="30%">

## Prerequisiti

- Stampante FDM con slicer conico installato (https://www.amazon.it/3DPLady-Stampante-aerografo-rimovibile-compatibile/dp/B09BWTGR3C)
- Python installato con Numpy Stl
- SuperSlicer installato (comprensivo di gcodeviewer)

### Istruzioni utilizzo interfaccia

- Scaricare directory ed aprire cartella interfacciaZ, avviare mainZ.py con VScode e successivamente eseguire il programma. Ci si troverà di fronte questa interfaccia utente:
<img src= "https://github.com/Ventiseidieci/InterfacciaZ/blob/main/images/conicstudio.png" width="50%" height="50%">

L'interfaccia permette di modificare l'angolo di slicing del modello, il fade base in mm (da quale altezza interviene la trasformazione) e il tipo di angolo, se "outward" o "inward".
È inoltre possibile indicare il punto di partenza sul piano del gcode, indicando in mm lo shift sugli assi X o Y corrispondente.
Successivamente troviamo le due tab di trasformazione. Il primo punto esegue la prima deformazionio del file STL selezionato, mentre il secondo punto esegue la retro trasformazione del Gcode generato, e quindi pronto per la stampa.

La procedura dettagliata è la seguente:
- Prepariamo un corpo con sbalzi importanti sul cad, aggiungendo un piano spesso pochi mm e grande quanto il piatto di stampa (nel nostro caso 300x300mm)(outbut: 2 corpi distinti)
- Lo esportiamo in una cartella che chiameremo "STL_trasformazione"
- Apriamo l'interfaccia "Conic Studio" eseguendola da VScode
- Selezionimo il file STL e lo trasformiamo
- Apriamo l'stl generato in Super slicer, lo centriamo sul piatto e separiamo i due corpi in parti. Il piano lo possiamo cancellare
- Ora eseguiamo lo slicing del corpo e salviamo il Gcode in una cartella che chiamerelo "Gcode_trasformazione"
- Il Gcode generato è pronto per essere stampato

Una volta avviato selezionare il file stl da convertire, dare un nome e premere "Trasforma STL" questo salverà il file in una cartella stl_transformed all'interno della directory del file.

Aprire l'STL da slicer e salvare gcode nella cartrella InterfacciaZ, seleziona GCode da interfaccia e cliccare Ritrasforma Gcode, il file verrà spostato nella cartella gcodes, mentre quello trasformato verrà salvato in gcodes_transformed. Entrambe le cartelle vengono create nella directory del file.

Buttare un occhio sul terminale di vscode per vedere quando i processi sono terminati
