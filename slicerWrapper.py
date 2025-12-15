import subprocess
import os
import sys

class SlicerWrapper:
    def __init__(self, slicer_path=""):
        self.slicer_path = slicer_path

    def set_slicer_path(self, path):
        self.slicer_path = path

    def slice_file(self, stl_path, output_gcode_path, config_path=None):
        """
        Esegue lo slicing usando PrusaSlicer/SuperSlicer da riga di comando.
        """
        if not os.path.exists(self.slicer_path):
            raise FileNotFoundError(f"Eseguibile slicer non trovato: {self.slicer_path}")
        
        if not os.path.exists(stl_path):
            raise FileNotFoundError(f"File STL non trovato: {stl_path}")

        # --- COSTRUZIONE COMANDO ---
        # L'ordine è CRUCIALE: prima carichiamo la config, poi i comandi di export, poi i file.
        cmd = [self.slicer_path]

        # 1. Carica Configurazione (PRIMA DI TUTTO)
        if config_path and os.path.exists(config_path):
            cmd.extend(["--load", config_path])
        
        # 2. Comandi di Export
        cmd.extend(["--export-gcode", "--output", output_gcode_path])
        
        # 3. File di Input (ALLA FINE)
        cmd.append(stl_path)
        
        # Debug: stampa il comando esatto per controllo
        print(f"DEBUG SLICER CMD: {' '.join(cmd)}")

        # --- ESECUZIONE ---
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Catturiamo sia stdout che stderr per vedere perché si blocca
        process = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)

        if process.returncode != 0:
            # Creiamo un report dettagliato dell'errore
            error_msg = f"ERRORE CRITICO SLICER (Codice {process.returncode}):\n"
            error_msg += f"--- STDOUT (Messaggi normali) ---\n{process.stdout}\n"
            error_msg += f"--- STDERR (Errori) ---\n{process.stderr}\n"
            print(error_msg) # Lo stampiamo anche in console
            raise Exception("Lo slicer ha fallito. Controlla la console per i dettagli.")
        
        # Se lo slicing ha successo, controlliamo se il file esiste davvero
        if not os.path.exists(output_gcode_path):
             # A volte lo slicer esce con codice 0 ma non salva nulla se il config è vuoto
             raise Exception("Lo slicer è terminato senza errori, ma il file Gcode non è stato creato. Probabile file .ini incompleto.")

        return True