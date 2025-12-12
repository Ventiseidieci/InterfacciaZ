import subprocess
import os
import sys

class SlicerWrapper:
    def __init__(self, slicer_path=""):
        # slicer_path deve puntare all'eseguibile (es. prusa-slicer-console.exe)
        self.slicer_path = slicer_path

    def set_slicer_path(self, path):
        self.slicer_path = path

    def slice_file(self, stl_path, output_gcode_path, config_path=None):
        """
        Esegue lo slicing usando PrusaSlicer da riga di comando.
        """
        if not os.path.exists(self.slicer_path):
            raise FileNotFoundError(f"Eseguibile slicer non trovato: {self.slicer_path}")
        
        if not os.path.exists(stl_path):
            raise FileNotFoundError(f"File STL non trovato: {stl_path}")

        # Costruzione del comando
        # Sintassi PrusaSlicer: prusa-slicer-console.exe --export-gcode --output output.gcode input.stl --load config.ini
        cmd = [
            self.slicer_path,
            "--export-gcode",
            "--output", output_gcode_path,
            stl_path
        ]

        if config_path and os.path.exists(config_path):
            cmd.extend(["--load", config_path])
        
        # Esecuzione comando (nascondendo la finestra su Windows)
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        print(f"Avvio slicing: {' '.join(cmd)}")
        process = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)

        if process.returncode != 0:
            raise Exception(f"Errore Slicing:\n{process.stderr}")
        
        return True