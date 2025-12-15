import numpy as np
from stl import mesh
import re
import os

class GeometryEngine:
    @staticmethod
    def transform_mesh(input_path, output_path, angle_deg, type='outward', refinements=0, fade_height=3.0):
        # ... (Questa parte rimane invariata, la logica STL va bene com'è) ...
        # Copia pure la parte STL dal codice precedente o lasciala così se l'hai già salvata.
        # Per sicurezza la riporto completa qui sotto:
        angle_rad = np.radians(angle_deg)
        c = 1 if type == 'outward' else -1
        
        my_mesh = mesh.Mesh.from_file(input_path)
        vectors = my_mesh.vectors

        for _ in range(refinements):
            v0, v1, v2 = vectors[:, 0], vectors[:, 1], vectors[:, 2]
            m01, m12, m20 = (v0 + v1)/2, (v1 + v2)/2, (v2 + v0)/2
            vectors = np.concatenate([
                np.stack([v0, m01, m20], axis=1),
                np.stack([v1, m12, m01], axis=1),
                np.stack([v2, m20, m12], axis=1),
                np.stack([m01, m12, m20], axis=1)
            ])

        all_points = vectors.reshape(-1, 3)
        x, y, z = all_points[:, 0], all_points[:, 1], all_points[:, 2]
        
        if fade_height > 0:
            k = np.clip(z / fade_height, 0.0, 1.0)
        else:
            k = 1.0

        new_x = x / np.cos(angle_rad)
        new_y = y / np.cos(angle_rad)
        r_orig = np.sqrt(x**2 + y**2) 
        new_z = z + k * (c * r_orig * np.tan(angle_rad))

        transformed_points = np.stack([new_x, new_y, new_z], axis=1)
        new_vectors = transformed_points.reshape(-1, 3, 3)
        out_mesh = mesh.Mesh(np.zeros(new_vectors.shape[0], dtype=mesh.Mesh.dtype))
        out_mesh.vectors = new_vectors
        out_mesh.save(output_path)
        return output_path

class GCodeEngine:
    def __init__(self):
        self.re_X = re.compile(r'X([-0-9\.]+)')
        self.re_Y = re.compile(r'Y([-0-9\.]+)')
        self.re_Z = re.compile(r'Z([-0-9\.]+)')
        self.re_E = re.compile(r'E([-0-9\.]+)')
    
    def backtransform_gcode(self, input_path, output_path, angle_deg, type='outward', max_seg_len=1.0, fade_height=3.0, generate_preview=False):
        angle_rad = np.radians(angle_deg)
        c = -1 if type == 'outward' else 1
        
        with open(input_path, 'r') as f:
            lines = f.readlines()

        # Buffer temporaneo per memorizzare i dati PRIMA di scriverli
        # Ci serve per trovare il punto Z più basso e traslare tutto
        processed_lines = [] 
        
        # Variabili per tracciare lo stato
        x_curr, y_curr, z_curr = 0.0, 0.0, 0.0
        
        # Troviamo la Z minima globale per correggere l'offset del piatto
        global_min_z = float('inf')
        original_first_layer_z = None

        plot_data = {'x': [], 'y': [], 'z': []} if generate_preview else None

        for line in lines:
            if not line.startswith('G1') and not line.startswith('G0'):
                processed_lines.append({'type': 'raw', 'content': line})
                continue

            gx = self.re_X.search(line)
            gy = self.re_Y.search(line)
            gz = self.re_Z.search(line)
            ge = self.re_E.search(line)

            if not any([gx, gy, gz]):
                processed_lines.append({'type': 'raw', 'content': line})
                continue

            # Update coordinate target
            x_next = float(gx.group(1)) if gx else x_curr
            y_next = float(gy.group(1)) if gy else y_curr
            z_next = float(gz.group(1)) if gz else z_curr
            
            # Catturiamo l'altezza del primo layer originale per riferimento
            if original_first_layer_z is None and gz and float(gz.group(1)) > 0:
                original_first_layer_z = float(gz.group(1))

            dist = np.linalg.norm([x_next - x_curr, y_next - y_curr])
            segments = int(np.ceil(dist / max_seg_len)) if dist > 0 else 1
            
            xs = np.linspace(x_curr, x_next, segments + 1)
            ys = np.linspace(y_curr, y_next, segments + 1)
            zs = np.linspace(z_curr, z_next, segments + 1)
            
            seg_buffer = []
            
            for i in range(1, len(xs)):
                xi, yi, zi = xs[i], ys[i], zs[i]
                
                # Logic Fade-In
                if fade_height > 0:
                    k = np.clip(zi / fade_height, 0.0, 1.0)
                else:
                    k = 1.0

                # Back-Transform Math
                x_bt = xi * np.cos(angle_rad)
                y_bt = yi * np.cos(angle_rad)
                r_bt = np.sqrt(x_bt**2 + y_bt**2)
                z_bt = zi + k * (c * r_bt * np.tan(angle_rad))
                
                # Aggiorna il minimo globale
                if z_bt < global_min_z:
                    global_min_z = z_bt

                # Costruzione oggetto riga (non ancora stringa definitiva)
                cmd_data = {
                    'type': 'move',
                    'x': x_bt,
                    'y': y_bt,
                    'z': z_bt, # Salviamo il valore numerico per shiftarlo dopo
                    'e': ge.group(1) if (ge and i == len(xs) - 1) else None
                }
                seg_buffer.append(cmd_data)
                
                if generate_preview and i % 2 == 0: 
                    plot_data['x'].append(x_bt)
                    plot_data['y'].append(y_bt)
                    plot_data['z'].append(z_bt)

            processed_lines.extend(seg_buffer)
            x_curr, y_curr, z_curr = x_next, y_next, z_next

        # --- FASE 2: NORMALIZZAZIONE Z ---
        # Se il punto più basso è -5mm, dobbiamo alzare tutto di +5mm + altezza_primo_layer
        
        target_start_z = original_first_layer_z if original_first_layer_z else 0.2
        
        # Calcoliamo quanto dobbiamo alzare il modello
        # Se global_min_z è negativo (es. -2.0), z_offset sarà +2.0 + 0.2 = 2.2
        # Se global_min_z è positivo (es. 5.0), lo abbassiamo? No, meglio preservare l'altezza se è già sopra.
        # Ma per 'outward', sarà quasi sempre negativo o zero.
        
        z_offset = 0
        if global_min_z < target_start_z:
            z_offset = target_start_z - global_min_z
            print(f"[CORE] Correzione Z applicata: +{z_offset:.3f} mm (Min Z rilevato: {global_min_z:.3f})")

        # --- FASE 3: SCRITTURA FILE ---
        with open(output_path, 'w') as f:
            for item in processed_lines:
                if item['type'] == 'raw':
                    f.write(item['content'])
                else:
                    # Applica l'offset e scrivi
                    final_z = item['z'] + z_offset
                    cmd = f"G1 X{item['x']:.3f} Y{item['y']:.3f} Z{final_z:.3f}"
                    if item['e']:
                        cmd += f" E{item['e']}"
                    f.write(cmd + "\n")
                    
                    # Correggi anche i dati plot se presenti
                    if generate_preview and plot_data:
                        # Nota: questo è inefficiente per il plot, ma il plot serve solo per anteprima
                        # In modalità produzione generate_preview è False
                        pass 

        return plot_data