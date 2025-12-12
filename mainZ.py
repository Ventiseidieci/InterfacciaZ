from tkinter import *
from tkinter import ttk, filedialog
import tkinter as tk
import os
import shutil

from transformSTL import stlTransformer
from backTransformGCode import gcodeTransformer

st = stlTransformer()
gt = gcodeTransformer( )

def open_stl_file():
     stl_file = filedialog.askopenfile(mode='r', filetypes=[('Fusion File', '*.stl'), ('All Files','*.*')])
     if stl_file:
          st.set_file_name(stl_file.name)
          directory = os.path.dirname(stl_file.name)
          os.makedirs(os.path.join(directory, 'stl_transformed'), exist_ok=True)
          

def open_gcode_file():
     gcode_file = filedialog.askopenfile(mode='r', filetypes=[('Gcode File', '*.gcode'), ('All Files','*.*')])
     if gcode_file:
          
          directory = os.path.dirname(gcode_file.name)
          baseName = os.path.basename(gcode_file.name)
          new_path = os.path.join(directory, 'gcodes', baseName)
          try:
               # Tenta di creare la cartella
               os.mkdir(os.path.join(directory, 'gcodes'))
               shutil.move(gcode_file.name, new_path)
               print(f"Cartella creata con successo in: {directory}")

          except FileExistsError:
               # Se la cartella esiste già, gestisci l'eccezione
               print(f"La cartella esiste già in: {directory}")
               shutil.move(gcode_file.name, new_path)
               
          try:
               # Tenta di creare la cartella
               os.mkdir(os.path.join(directory, 'gcodes_backtransformed'))
               print(f"Cartella creata con successo in: {directory}")

          except FileExistsError:
               # Se la cartella esiste già, gestisci l'eccezione
               print(f"La cartella esiste già in: {directory}")
               
          gt.set_file_name(new_path)
          
root = Tk()
root.geometry("550x90")
frmTop = ttk.Frame(root, padding=5)
frmTop.pack(fill=X)
frmBottom = ttk.Frame(root, padding=5)
frmBottom.pack(fill=X, side= BOTTOM)
stlNewName = tk.StringVar()
gcodeNewName = tk.StringVar()

# STL PART
ttk.Button(frmTop, text="seleziona STL", command=open_stl_file, label="inserisci nome file").pack(pady=2, padx=2, side=LEFT, fill=X, ipady=1)
inputtxt = Entry(frmTop, textvariable=stlNewName)
inputtxt.pack(side=LEFT, fill=X, padx=2)
ttk.Button(frmTop, text="Transforma STL", command=lambda:st.start(stlNewName.get())).pack(pady=2, padx=2,side=LEFT, fill=X, ipady=1)


# GCODE PART
ttk.Button(frmBottom, text="seleziona Gcode", command=open_gcode_file).pack(pady=2, padx=2, side=LEFT, fill=X, ipady=1)
ttk.Button(frmBottom, text="Ritrasforma Gcode", command=lambda:gt.start()).pack(pady=2, padx=2,side=LEFT, fill=X, ipady=1)

root.mainloop()