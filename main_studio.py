import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys
import os
import queue

# Assicurati che conic_core.py sia aggiornato
from conic_core import GeometryEngine, GCodeEngine

class AsyncConsole:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.text_widget.tag_configure("info", foreground="#55ff55")
        self.update_widget()
    def write(self, msg): self.queue.put(msg)
    def flush(self): pass
    def update_widget(self):
        try:
            while not self.queue.empty():
                msg = self.queue.get_nowait()
                self.text_widget.insert(tk.END, msg)
                self.text_widget.see(tk.END)
                self.queue.task_done()
        except queue.Empty: pass
        self.text_widget.after(100, self.update_widget)

class ConicStudioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CONIC STUDIO - Lite Edition (With Shift)")
        self.geometry("650x700") # Leggermente più alta
        
        self.stl_path = tk.StringVar()
        self.gcode_path = tk.StringVar()
        self.status_var = tk.StringVar(value="Sistema Pronto.")
        
        self.geo_engine = GeometryEngine()
        self.gcode_engine = GCodeEngine()

        self._setup_ui()
        self.console = AsyncConsole(self.console_log)
        sys.stdout = self.console

    def _setup_ui(self):
        style = ttk.Style()
        style.configure("Bold.TButton", font=('Segoe UI','10','bold'))

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- PARAMETRI ---
        lbl_p = ttk.LabelFrame(main_frame, text="Parametri Generali", padding=10)
        lbl_p.pack(fill=tk.X, pady=5)
        
        # Riga 1: Angolo, Fade, Tipo
        f_row1 = ttk.Frame(lbl_p)
        f_row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(f_row1, text="Angolo (°):").pack(side=tk.LEFT, padx=5)
        self.spin_angle = ttk.Spinbox(f_row1, from_=0, to=60, width=5)
        self.spin_angle.set(16)
        self.spin_angle.pack(side=tk.LEFT)
        
        ttk.Label(f_row1, text="Fade Base (mm):").pack(side=tk.LEFT, padx=5)
        self.spin_fade = ttk.Spinbox(f_row1, from_=0, to=50, width=5)
        self.spin_fade.set(3.0)
        self.spin_fade.pack(side=tk.LEFT)
        
        ttk.Label(f_row1, text="Tipo:").pack(side=tk.LEFT, padx=5)
        self.combo_type = ttk.Combobox(f_row1, values=["outward", "inward"], width=8, state="readonly")
        self.combo_type.set("outward")
        self.combo_type.pack(side=tk.LEFT)

        # Riga 2: Shift X / Y
        f_row2 = ttk.Frame(lbl_p)
        f_row2.pack(fill=tk.X, pady=5)
        
        ttk.Label(f_row2, text="Shift X (mm):").pack(side=tk.LEFT, padx=5)
        self.spin_shift_x = ttk.Spinbox(f_row2, from_=-500, to=500, width=6)
        self.spin_shift_x.set(0) # Default 0 (se hai slicato al centro, metti 0. Se hai slicato a 0,0, metti 110)
        self.spin_shift_x.pack(side=tk.LEFT)
        
        ttk.Label(f_row2, text="Shift Y (mm):").pack(side=tk.LEFT, padx=5)
        self.spin_shift_y = ttk.Spinbox(f_row2, from_=-500, to=500, width=6)
        self.spin_shift_y.set(0)
        self.spin_shift_y.pack(side=tk.LEFT)

        # --- STL ---
        lbl_f = ttk.LabelFrame(main_frame, text="1. Trasforma STL", padding=10)
        lbl_f.pack(fill=tk.X, pady=10)
        
        f_sel_stl = ttk.Frame(lbl_f)
        f_sel_stl.pack(fill=tk.X)
        ttk.Button(f_sel_stl, text="Scegli File STL", command=self.load_stl).pack(side=tk.LEFT)
        ttk.Label(f_sel_stl, textvariable=self.stl_path, font=("Consolas", 8)).pack(side=tk.LEFT, padx=5)
        
        self.btn_transform = ttk.Button(lbl_f, text=">>> ESEGUI TRASFORMAZIONE STL >>>", command=self.run_transform_stl, style="Bold.TButton")
        self.btn_transform.pack(fill=tk.X, pady=5)

        # --- GCODE ---
        lbl_g = ttk.LabelFrame(main_frame, text="2. Finalizza Gcode", padding=10)
        lbl_g.pack(fill=tk.X, pady=10)
        
        f_sel_gcode = ttk.Frame(lbl_g)
        f_sel_gcode.pack(fill=tk.X)
        ttk.Button(f_sel_gcode, text="Scegli File Gcode", command=self.load_gcode).pack(side=tk.LEFT)
        ttk.Label(f_sel_gcode, textvariable=self.gcode_path, font=("Consolas", 8)).pack(side=tk.LEFT, padx=5)
        
        self.btn_backtrans = ttk.Button(lbl_g, text=">>> FINALIZZA GCODE >>>", command=self.run_backtransform, style="Bold.TButton")
        self.btn_backtrans.pack(fill=tk.X, pady=5)

        # Console
        ttk.Label(main_frame, text="Log:").pack(anchor="w")
        self.console_log = tk.Text(main_frame, height=15, bg="#101010", fg="#eeeeee", font=("Consolas", 9), insertbackground="white")
        self.console_log.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w").pack(side=tk.BOTTOM, fill=tk.X)

    def load_stl(self):
        f = filedialog.askopenfilename(filetypes=[("STL", "*.stl")])
        if f: self.stl_path.set(f)
    def load_gcode(self):
        f = filedialog.askopenfilename(filetypes=[("Gcode", "*.gcode")])
        if f: self.gcode_path.set(f)

    def run_transform_stl(self):
        path = self.stl_path.get()
        if not path:
            messagebox.showwarning("Stop", "Seleziona STL!")
            return
        
        self.btn_transform.config(state="disabled")
        self.status_var.set("Elaborazione STL...")
        self.update_idletasks()

        def task():
            try:
                angle = float(self.spin_angle.get())
                fade = float(self.spin_fade.get())
                ctype = self.combo_type.get()
                out = path.replace(".stl", f"_base{int(fade)}mm_conic.stl")
                
                print(f"\n--- STL START ---")
                print(f"Angolo: {angle}°, Fade: {fade}mm")
                self.geo_engine.transform_mesh(path, out, angle, ctype, refinements=0, fade_height=fade)
                print(f"Salvato: {os.path.basename(out)}")
                self.status_var.set("STL Pronto.")
            except Exception as e:
                print(f"Errore: {e}")
            finally:
                self.after(0, lambda: self.btn_transform.config(state="normal"))
        threading.Thread(target=task, daemon=True).start()

    def run_backtransform(self):
        path = self.gcode_path.get()
        if not path:
            messagebox.showwarning("Stop", "Seleziona Gcode!")
            return

        self.btn_backtrans.config(state="disabled")
        self.status_var.set("Elaborazione Gcode...")
        self.update_idletasks()

        def task():
            try:
                angle = float(self.spin_angle.get())
                fade = float(self.spin_fade.get())
                ctype = self.combo_type.get()
                sx = float(self.spin_shift_x.get())
                sy = float(self.spin_shift_y.get())
                
                out = path.replace(".gcode", "_FINAL.gcode")
                
                print(f"\n--- GCODE START ---")
                print(f"Shift X: {sx}, Shift Y: {sy}")
                self.gcode_engine.backtransform_gcode(path, out, angle, ctype, fade_height=fade, shift_x=sx, shift_y=sy, generate_preview=False)
                
                print(f"File Finale: {os.path.basename(out)}")
                self.status_var.set("Finito!")
            except Exception as e:
                print(f"Errore: {e}")
            finally:
                self.after(0, lambda: self.btn_backtrans.config(state="normal"))
        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    app = ConicStudioApp()
    app.mainloop()
    import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys
import os
import queue

# Assicurati che conic_core.py sia aggiornato
from conic_core import GeometryEngine, GCodeEngine

class AsyncConsole:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.text_widget.tag_configure("info", foreground="#55ff55")
        self.update_widget()
    def write(self, msg): self.queue.put(msg)
    def flush(self): pass
    def update_widget(self):
        try:
            while not self.queue.empty():
                msg = self.queue.get_nowait()
                self.text_widget.insert(tk.END, msg)
                self.text_widget.see(tk.END)
                self.queue.task_done()
        except queue.Empty: pass
        self.text_widget.after(100, self.update_widget)

class ConicStudioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CONIC STUDIO - Lite Edition (With Shift)")
        self.geometry("650x700") # Leggermente più alta
        
        self.stl_path = tk.StringVar()
        self.gcode_path = tk.StringVar()
        self.status_var = tk.StringVar(value="Sistema Pronto.")
        
        self.geo_engine = GeometryEngine()
        self.gcode_engine = GCodeEngine()

        self._setup_ui()
        self.console = AsyncConsole(self.console_log)
        sys.stdout = self.console

    def _setup_ui(self):
        style = ttk.Style()
        style.configure("Bold.TButton", font=('Segoe UI','10','bold'))

        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- PARAMETRI ---
        lbl_p = ttk.LabelFrame(main_frame, text="Parametri Generali", padding=10)
        lbl_p.pack(fill=tk.X, pady=5)
        
        # Riga 1: Angolo, Fade, Tipo
        f_row1 = ttk.Frame(lbl_p)
        f_row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(f_row1, text="Angolo (°):").pack(side=tk.LEFT, padx=5)
        self.spin_angle = ttk.Spinbox(f_row1, from_=0, to=60, width=5)
        self.spin_angle.set(16)
        self.spin_angle.pack(side=tk.LEFT)
        
        ttk.Label(f_row1, text="Fade Base (mm):").pack(side=tk.LEFT, padx=5)
        self.spin_fade = ttk.Spinbox(f_row1, from_=0, to=50, width=5)
        self.spin_fade.set(3.0)
        self.spin_fade.pack(side=tk.LEFT)
        
        ttk.Label(f_row1, text="Tipo:").pack(side=tk.LEFT, padx=5)
        self.combo_type = ttk.Combobox(f_row1, values=["outward", "inward"], width=8, state="readonly")
        self.combo_type.set("outward")
        self.combo_type.pack(side=tk.LEFT)

        # Riga 2: Shift X / Y
        f_row2 = ttk.Frame(lbl_p)
        f_row2.pack(fill=tk.X, pady=5)
        
        ttk.Label(f_row2, text="Shift X (mm):").pack(side=tk.LEFT, padx=5)
        self.spin_shift_x = ttk.Spinbox(f_row2, from_=-500, to=500, width=6)
        self.spin_shift_x.set(0) # Default 0 (se hai slicato al centro, metti 0. Se hai slicato a 0,0, metti 110)
        self.spin_shift_x.pack(side=tk.LEFT)
        
        ttk.Label(f_row2, text="Shift Y (mm):").pack(side=tk.LEFT, padx=5)
        self.spin_shift_y = ttk.Spinbox(f_row2, from_=-500, to=500, width=6)
        self.spin_shift_y.set(0)
        self.spin_shift_y.pack(side=tk.LEFT)

        # --- STL ---
        lbl_f = ttk.LabelFrame(main_frame, text="1. Trasforma STL", padding=10)
        lbl_f.pack(fill=tk.X, pady=10)
        
        f_sel_stl = ttk.Frame(lbl_f)
        f_sel_stl.pack(fill=tk.X)
        ttk.Button(f_sel_stl, text="Scegli File STL", command=self.load_stl).pack(side=tk.LEFT)
        ttk.Label(f_sel_stl, textvariable=self.stl_path, font=("Consolas", 8)).pack(side=tk.LEFT, padx=5)
        
        self.btn_transform = ttk.Button(lbl_f, text=">>> ESEGUI TRASFORMAZIONE STL >>>", command=self.run_transform_stl, style="Bold.TButton")
        self.btn_transform.pack(fill=tk.X, pady=5)

        # --- GCODE ---
        lbl_g = ttk.LabelFrame(main_frame, text="2. Finalizza Gcode", padding=10)
        lbl_g.pack(fill=tk.X, pady=10)
        
        f_sel_gcode = ttk.Frame(lbl_g)
        f_sel_gcode.pack(fill=tk.X)
        ttk.Button(f_sel_gcode, text="Scegli File Gcode", command=self.load_gcode).pack(side=tk.LEFT)
        ttk.Label(f_sel_gcode, textvariable=self.gcode_path, font=("Consolas", 8)).pack(side=tk.LEFT, padx=5)
        
        self.btn_backtrans = ttk.Button(lbl_g, text=">>> FINALIZZA GCODE >>>", command=self.run_backtransform, style="Bold.TButton")
        self.btn_backtrans.pack(fill=tk.X, pady=5)

        # Console
        ttk.Label(main_frame, text="Log:").pack(anchor="w")
        self.console_log = tk.Text(main_frame, height=15, bg="#101010", fg="#eeeeee", font=("Consolas", 9), insertbackground="white")
        self.console_log.pack(fill=tk.BOTH, expand=True, pady=5)
        
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w").pack(side=tk.BOTTOM, fill=tk.X)

    def load_stl(self):
        f = filedialog.askopenfilename(filetypes=[("STL", "*.stl")])
        if f: self.stl_path.set(f)
    def load_gcode(self):
        f = filedialog.askopenfilename(filetypes=[("Gcode", "*.gcode")])
        if f: self.gcode_path.set(f)

    def run_transform_stl(self):
        path = self.stl_path.get()
        if not path:
            messagebox.showwarning("Stop", "Seleziona STL!")
            return
        
        self.btn_transform.config(state="disabled")
        self.status_var.set("Elaborazione STL...")
        self.update_idletasks()

        def task():
            try:
                angle = float(self.spin_angle.get())
                fade = float(self.spin_fade.get())
                ctype = self.combo_type.get()
                out = path.replace(".stl", f"_base{int(fade)}mm_conic.stl")
                
                print(f"\n--- STL START ---")
                print(f"Angolo: {angle}°, Fade: {fade}mm")
                self.geo_engine.transform_mesh(path, out, angle, ctype, refinements=0, fade_height=fade)
                print(f"Salvato: {os.path.basename(out)}")
                self.status_var.set("STL Pronto.")
            except Exception as e:
                print(f"Errore: {e}")
            finally:
                self.after(0, lambda: self.btn_transform.config(state="normal"))
        threading.Thread(target=task, daemon=True).start()

    def run_backtransform(self):
        path = self.gcode_path.get()
        if not path:
            messagebox.showwarning("Stop", "Seleziona Gcode!")
            return

        self.btn_backtrans.config(state="disabled")
        self.status_var.set("Elaborazione Gcode...")
        self.update_idletasks()

        def task():
            try:
                angle = float(self.spin_angle.get())
                fade = float(self.spin_fade.get())
                ctype = self.combo_type.get()
                sx = float(self.spin_shift_x.get())
                sy = float(self.spin_shift_y.get())
                
                out = path.replace(".gcode", "_FINAL.gcode")
                
                print(f"\n--- GCODE START ---")
                print(f"Shift X: {sx}, Shift Y: {sy}")
                self.gcode_engine.backtransform_gcode(path, out, angle, ctype, fade_height=fade, shift_x=sx, shift_y=sy, generate_preview=False)
                
                print(f"File Finale: {os.path.basename(out)}")
                self.status_var.set("Finito!")
            except Exception as e:
                print(f"Errore: {e}")
            finally:
                self.after(0, lambda: self.btn_backtrans.config(state="normal"))
        threading.Thread(target=task, daemon=True).start()

if __name__ == "__main__":
    app = ConicStudioApp()
    app.mainloop()