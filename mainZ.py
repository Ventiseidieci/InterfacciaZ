import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import threading # Per non bloccare l'interfaccia
import configparser

from transformSTL import stlTransformer
from backTransformGCode import gcodeTransformer
from slicerWrapper import SlicerWrapper

# Inizializzazione classi
st = stlTransformer()
gt = gcodeTransformer()
sw = SlicerWrapper()

# Variabili globali per percorsi
current_stl_path = None
current_transformed_stl_path = None # Percorso dell'STL trasformato
current_gcode_path = None
directory_base = None

def run_threaded(target_func):
    """Esegue una funzione in un thread separato"""
    threading.Thread(target=target_func).start()

def log_status(message):
    lbl_status.config(text=message)
    print(message)

# --- FUNZIONI STL ---
def open_stl_file():
     global current_stl_path, directory_base
     stl_file = filedialog.askopenfile(mode='r', filetypes=[('STL File', '*.stl'), ('All Files','*.*')])
     if stl_file:
          current_stl_path = stl_file.name
          st.set_file_name(current_stl_path)
          directory_base = os.path.dirname(current_stl_path)
          lbl_stl_path.config(text=os.path.basename(current_stl_path))
          
          # Prepara cartella output STL
          output_folder = os.path.join(directory_base, 'stl_transformed')
          os.makedirs(output_folder, exist_ok=True)
          st.set_folder_name_transformed(output_folder)

def process_stl():
    if not current_stl_path:
        messagebox.showwarning("Attenzione", "Seleziona prima un file STL")
        return
    
    name = stlNewName.get()
    if not name:
        name = "output"

    btn_transf_stl.config(state="disabled")
    log_status("Trasformazione STL in corso...")

    try:
        # Esegue trasformazione e ottiene il percorso del file creato
        global current_transformed_stl_path
        current_transformed_stl_path = st.start(name)
        log_status(f"STL Trasformato: {os.path.basename(current_transformed_stl_path)}")
        messagebox.showinfo("Fatto", "STL Trasformato correttamente!")
    except Exception as e:
        log_status(f"Errore STL: {e}")
        messagebox.showerror("Errore", str(e))
    finally:
        btn_transf_stl.config(state="normal")

# --- FUNZIONI SLICER ---
def select_slicer_exe():
    exe_path = filedialog.askopenfilename(title="Seleziona PrusaSlicer Console", filetypes=[("Executable", "*.exe")])
    if exe_path:
        sw.set_slicer_path(exe_path)
        lbl_slicer_path.config(text=os.path.basename(exe_path))

def select_slicer_config():
    ini_path = filedialog.askopenfilename(title="Seleziona Configurazione Slicer", filetypes=[("Config INI", "*.ini")])
    if ini_path:
        path_config_var.set(ini_path)
        lbl_config_path.config(text=os.path.basename(ini_path))

def process_slicing():
    global current_transformed_stl_path, directory_base, current_gcode_path
    
    if not current_transformed_stl_path or not os.path.exists(current_transformed_stl_path):
        messagebox.showwarning("Attenzione", "Devi prima trasformare un STL!")
        return
    
    if not sw.slicer_path:
        messagebox.showwarning("Attenzione", "Seleziona l'eseguibile dello slicer (prusa-slicer-console.exe)")
        return

    # Cartella output Gcode
    output_folder_gcodes = os.path.join(directory_base, 'gcodes')
    os.makedirs(output_folder_gcodes, exist_ok=True)
    
    # Nome file output
    base_name = os.path.splitext(os.path.basename(current_transformed_stl_path))[0]
    output_gcode = os.path.join(output_folder_gcodes, base_name + ".gcode")

    btn_slice.config(state="disabled")
    log_status("Slicing in corso (attendere)...")

    def thread_task():
        try:
            sw.slice_file(current_transformed_stl_path, output_gcode, path_config_var.get())
            
            # Aggiorna variabili per il prossimo step (Ritrasformazione GCode)
            global current_gcode_path
            current_gcode_path = output_gcode
            gt.set_file_name(current_gcode_path)
            
            # Aggiorna UI dal thread principale
            root.after(0, lambda: log_status("Slicing Completato!"))
            root.after(0, lambda: lbl_gcode_path.config(text=os.path.basename(output_gcode)))
            root.after(0, lambda: messagebox.showinfo("Fatto", "GCode Generato! Ora puoi ritrasformarlo."))
        except Exception as e:
            root.after(0, lambda: log_status(f"Errore Slicing: {e}"))
            root.after(0, lambda: messagebox.showerror("Errore Slicing", str(e)))
        finally:
            root.after(0, lambda: btn_slice.config(state="normal"))

    run_threaded(thread_task)

# --- FUNZIONI GCODE ---
def open_gcode_file_manual():
    """Per selezionare manualmente un Gcode se non si usa il flusso automatico"""
    global current_gcode_path, directory_base
    gcode_file = filedialog.askopenfile(mode='r', filetypes=[('Gcode File', '*.gcode'), ('All Files','*.*')])
    if gcode_file:
        path = gcode_file.name
        directory_base = os.path.dirname(path)
        
        # Sposta in 'gcodes' se non è già lì (logica vecchia mantenuta)
        folder_gcodes = os.path.join(directory_base, 'gcodes')
        os.makedirs(folder_gcodes, exist_ok=True)
        
        if os.path.dirname(path) != folder_gcodes:
            new_path = os.path.join(folder_gcodes, os.path.basename(path))
            try:
                shutil.move(path, new_path)
                path = new_path
            except:
                pass # Se esiste già o errore, usa quello che c'è
        
        current_gcode_path = path
        gt.set_file_name(current_gcode_path)
        
        # Prepara cartella output
        os.makedirs(os.path.join(directory_base, 'gcodes_backtransformed'), exist_ok=True)
        
        lbl_gcode_path.config(text=os.path.basename(current_gcode_path))

def process_backtransform():
    if not current_gcode_path:
        messagebox.showwarning("Attenzione", "Nessun GCode selezionato o generato")
        return

    btn_transf_gcode.config(state="disabled")
    log_status("Ritrasformazione GCode in corso...")
    
    # Setup parametri GCode Transformer (esempio fisso, idealmente collegare a UI)
    gt.set_file_name(current_gcode_path)
    
    def thread_task():
        try:
            gt.start() # Assicurati che backTransformGCode gestisca i path relativi correttamente o usa path assoluti
            root.after(0, lambda: log_status("Ciclo Completo Terminato!"))
            root.after(0, lambda: messagebox.showinfo("Successo", "Processo completato!"))
        except Exception as e:
            root.after(0, lambda: log_status(f"Errore GCode: {e}"))
        finally:
             root.after(0, lambda: btn_transf_gcode.config(state="normal"))

    run_threaded(thread_task)


# --- GUI LAYOUT ---
root = tk.Tk()
root.title("InterfacciaZ - Pipeline Completa")
root.geometry("600x450")

path_config_var = tk.StringVar()
stlNewName = tk.StringVar(value="torre")

# Frame Principale
main_frame = ttk.Frame(root, padding=10)
main_frame.pack(fill=tk.BOTH, expand=True)

# SEZIONE 1: STL
step1 = ttk.LabelFrame(main_frame, text="1. Trasformazione STL", padding=10)
step1.pack(fill=tk.X, pady=5)

ttk.Button(step1, text="Seleziona STL Originale", command=open_stl_file).pack(side=tk.LEFT, padx=5)
lbl_stl_path = ttk.Label(step1, text="Nessun file", foreground="gray")
lbl_stl_path.pack(side=tk.LEFT, padx=5)

frame_name = ttk.Frame(step1)
frame_name.pack(fill=tk.X, pady=5)
ttk.Label(frame_name, text="Nome Output:").pack(side=tk.LEFT)
ttk.Entry(frame_name, textvariable=stlNewName, width=15).pack(side=tk.LEFT, padx=5)
btn_transf_stl = ttk.Button(frame_name, text="Trasforma STL", command=lambda: run_threaded(process_stl))
btn_transf_stl.pack(side=tk.RIGHT, padx=5)

# SEZIONE 2: SLICING
step2 = ttk.LabelFrame(main_frame, text="2. Slicing (PrusaSlicer)", padding=10)
step2.pack(fill=tk.X, pady=5)

f_slicer = ttk.Frame(step2)
f_slicer.pack(fill=tk.X)
ttk.Button(f_slicer, text="Exe Slicer", command=select_slicer_exe, width=15).pack(side=tk.LEFT, padx=5)
lbl_slicer_path = ttk.Label(f_slicer, text="Seleziona prusa-slicer-console.exe...", foreground="red")
lbl_slicer_path.pack(side=tk.LEFT, padx=5)

f_config = ttk.Frame(step2)
f_config.pack(fill=tk.X, pady=2)
ttk.Button(f_config, text="Config .ini", command=select_slicer_config, width=15).pack(side=tk.LEFT, padx=5)
lbl_config_path = ttk.Label(f_config, text="Seleziona config.ini", foreground="gray")
lbl_config_path.pack(side=tk.LEFT, padx=5)

btn_slice = ttk.Button(step2, text="Esegui Slicing (Genera Gcode)", command=process_slicing)
btn_slice.pack(fill=tk.X, pady=5, padx=5)

# SEZIONE 3: GCODE
step3 = ttk.LabelFrame(main_frame, text="3. Ritrasformazione GCode", padding=10)
step3.pack(fill=tk.X, pady=5)

f_gcode = ttk.Frame(step3)
f_gcode.pack(fill=tk.X)
ttk.Button(f_gcode, text="Seleziona Gcode (Opzionale)", command=open_gcode_file_manual).pack(side=tk.LEFT, padx=5)
lbl_gcode_path = ttk.Label(f_gcode, text="In attesa di slicing...", foreground="blue")
lbl_gcode_path.pack(side=tk.LEFT, padx=5)

btn_transf_gcode = ttk.Button(step3, text="Ritrasforma Gcode Finale", command=process_backtransform)
btn_transf_gcode.pack(fill=tk.X, pady=5, padx=5)

# BARRA DI STATO
lbl_status = ttk.Label(root, text="Pronto", relief=tk.SUNKEN, anchor=tk.W)
lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

root.mainloop()