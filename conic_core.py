import numpy as np
from stl import mesh
import re
import os

class GeometryEngine:
    @staticmethod
    def transform_mesh(input_path, output_path, angle_deg, type='outward', refinements=0, fade_height=3.0):
        # --- LOGICA STL INVARIATA ---
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
        self.re_G92 = re.compile(r'G92.*E([-0-9\.]+)')
    
    def backtransform_gcode(self, input_path, output_path, angle_deg, type='outward', max_seg_len=1.0, fade_height=3.0, shift_x=0.0, shift_y=0.0, generate_preview=False):
        """
        Esegue la ritrasformazione conica e applica uno shift X/Y finale.
        """
        angle_rad = np.radians(angle_deg)
        c = -1 if type == 'outward' else 1
        
        with open(input_path, 'r') as f:
            lines = f.readlines()

        new_lines = []
        x_curr, y_curr, z_curr, e_curr = 0.0, 0.0, 0.0, 0.0
        first_layer_z = 0.2
        found_first_layer = False
        
        plot_data = {'x': [], 'y': [], 'z': []} if generate_preview else None

        for line in lines:
            if 'G92' in line:
                m_g92 = self.re_G92.search(line)
                if m_g92: e_curr = float(m_g92.group(1))
                new_lines.append(line)
                continue

            if not line.startswith('G1') and not line.startswith('G0'):
                new_lines.append(line)
                continue

            gx = self.re_X.search(line)
            gy = self.re_Y.search(line)
            gz = self.re_Z.search(line)
            ge = self.re_E.search(line)

            if not any([gx, gy, gz, ge]):
                new_lines.append(line)
                continue

            x_next = float(gx.group(1)) if gx else x_curr
            y_next = float(gy.group(1)) if gy else y_curr
            z_next = float(gz.group(1)) if gz else z_curr
            e_next = float(ge.group(1)) if ge else e_curr

            if not found_first_layer and gz:
                z_val = float(gz.group(1))
                if z_val > 0.05:
                    first_layer_z = z_val
                    found_first_layer = True

            dist = np.linalg.norm([x_next - x_curr, y_next - y_curr])
            segments = int(np.ceil(dist / max_seg_len)) if dist > 0 else 1
            
            xs = np.linspace(x_curr, x_next, segments + 1)
            ys = np.linspace(y_curr, y_next, segments + 1)
            zs = np.linspace(z_curr, z_next, segments + 1)
            es = np.linspace(e_curr, e_next, segments + 1)
            
            seg_buffer = []
            
            for i in range(1, len(xs)):
                xi, yi, zi = xs[i], ys[i], zs[i]
                ei = es[i]
                
                if fade_height > 0:
                    k = np.clip(zi / fade_height, 0.0, 1.0)
                else:
                    k = 1.0

                # 1. Calcolo coordinate coniche (intorno a 0,0)
                x_bt = xi * np.cos(angle_rad)
                y_bt = yi * np.cos(angle_rad)
                r_bt = np.sqrt(x_bt**2 + y_bt**2)
                z_bt = zi + k * (c * r_bt * np.tan(angle_rad))
                
                # 2. Z Clamping
                if z_bt < first_layer_z:
                    z_bt = first_layer_z

                # 3. Applicazione Shift X/Y (Spostamento sul piatto)
                x_final = x_bt + shift_x
                y_final = y_bt + shift_y

                # Scrittura comando
                cmd = f"G1 X{x_final:.3f} Y{y_final:.3f} Z{z_bt:.3f}"
                if ge: 
                    cmd += f" E{ei:.5f}"
                
                seg_buffer.append(cmd + "\n")
                
                if generate_preview and i % 2 == 0: 
                    plot_data['x'].append(x_final)
                    plot_data['y'].append(y_final)
                    plot_data['z'].append(z_bt)

            new_lines.extend(seg_buffer)
            x_curr, y_curr, z_curr, e_curr = x_next, y_next, z_next, e_next

        with open(output_path, 'w') as f:
            f.writelines(new_lines)
            
        return plot_data