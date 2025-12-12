import re
import numpy as np
import time
import os

class gcodeTransformer():
    
    def __init__(self, file_name = None, folder_name = None, cone_angle=16, cone_type='outward', first_layer_height=0.2, x_shift=110, y_shift = 90):
        self._file_name = file_name
        self._folder_name = folder_name # Cartella di output opzionale
        self._cone_angle = cone_angle
        self._cone_type = cone_type
        self._first_layer_height = first_layer_height
        self._x_shift = x_shift
        self._y_shift = y_shift

    # --- GETTERS E SETTERS SEMPLIFICATI ---
    def set_file_name(self, value): self._file_name = value
    def get_file_name(self): return self._file_name
    
    def set_output_folder(self, value): self._folder_name = value
    
    def set_cone_angle(self, value): self._cone_angle = value
    def set_cone_type(self, value): self._cone_type = value

    # --- METODI DI ELABORAZIONE ---

    def insert_Z(self, row, z_value):
        pattern_X = r'X[-0-9]*[.]?[0-9]*'
        pattern_Y = r'Y[-0-9]*[.]?[0-9]*'
        pattern_Z = r'Z[-0-9]*[.]?[0-9]*'
        match_x = re.search(pattern_X, row)
        match_y = re.search(pattern_Y, row)
        match_z = re.search(pattern_Z, row)

        if match_z is not None:
            row_new = re.sub(pattern_Z, ' Z' + str(round(z_value, 3)), row)
        else:
            if match_y is not None:
                row_new = row[0:match_y.end(0)] + ' Z' + str(round(z_value, 3)) + row[match_y.end(0):]
            elif match_x is not None:
                row_new = row[0:match_x.end(0)] + ' Z' + str(round(z_value, 3)) + row[match_x.end(0):]
            else:
                row_new = 'Z' + str(round(z_value, 3)) + ' ' + row
        return row_new

    def replace_E(self, row, dist_old, dist_new, corr_value):
        pattern_E = r'E[-0-9]*[.]?[0-9]*'
        match_e = re.search(pattern_E, row)
        if match_e is None:
            return row
        e_val_old = float(match_e.group(0).replace('E', ''))
        if dist_old == 0:
            e_val_new = 0
        else:
            e_val_new = e_val_old * dist_new * corr_value / dist_old
        e_str_new = 'E' + f'{e_val_new:.5f}'
        row_new = row[0:match_e.start(0)] + e_str_new + row[match_e.end(0):]
        return row_new

    def backtransform_data_radial(self, data, cone_type, maximal_length, cone_angle_rad):
        new_data = []
        pattern_X = r'X[-0-9]*[.]?[0-9]*'
        pattern_Y = r'Y[-0-9]*[.]?[0-9]*'
        pattern_Z = r'Z[-0-9]*[.]?[0-9]*'
        pattern_E = r'E[-0-9]*[.]?[0-9]*'
        pattern_G = r'\AG[1] '

        x_old, y_old = 0, 0
        x_new, y_new = 0, 0
        z_layer = 0
        z_max = 0
        update_x, update_y = False, False
        
        if cone_type == 'outward':
            c = -1
            inward_cone = False
        elif cone_type == 'inward':
            c = 1
            inward_cone = True
        else:
            raise ValueError('{} is not a admissible type for the transformation'.format(cone_type))

        for row in data:
            g_match = re.search(pattern_G, row)
            if g_match is None:
                new_data.append(row)
            else:
                x_match = re.search(pattern_X, row)
                y_match = re.search(pattern_Y, row)
                z_match = re.search(pattern_Z, row)

                if x_match is None and y_match is None and z_match is None:
                    new_data.append(row)
                else:
                    if z_match is not None:
                        z_layer = float(z_match.group(0).replace('Z', ''))
                    if x_match is not None:
                        x_new = float(x_match.group(0).replace('X', ''))
                        update_x = True
                    if y_match is not None:
                        y_new = float(y_match.group(0).replace('Y', ''))
                        update_y = True

                    e_match = re.search(pattern_E, row)
                    x_old_bt, x_new_bt = x_old * np.cos(cone_angle_rad), x_new * np.cos(cone_angle_rad)
                    y_old_bt, y_new_bt = y_old * np.cos(cone_angle_rad), y_new * np.cos(cone_angle_rad)
                    dist_transformed = np.linalg.norm([x_new - x_old, y_new - y_old])

                    num_segm = int(dist_transformed // maximal_length + 1)
                    x_vals = np.linspace(x_old_bt, x_new_bt, num_segm + 1)
                    y_vals = np.linspace(y_old_bt, y_new_bt, num_segm + 1)
                    
                    if inward_cone and e_match is None and (update_x or update_y):
                        z_start = z_layer + c * np.sqrt(x_old_bt ** 2 + y_old_bt ** 2) * np.tan(cone_angle_rad)
                        z_end = z_layer + c * np.sqrt(x_new_bt ** 2 + y_new_bt ** 2) * np.tan(cone_angle_rad)
                        z_vals = np.linspace(z_start, z_end, num_segm + 1)
                    else:
                        z_vals = np.array([z_layer + c * np.sqrt(x ** 2 + y ** 2) * np.tan(cone_angle_rad) for x, y in zip(x_vals, y_vals)])
                        if e_match and (np.max(z_vals) > z_max or z_max == 0):
                            z_max = np.max(z_vals)
                        if e_match is None and np.max(z_vals) > z_max:
                            np.minimum(z_vals, (z_max + 1), z_vals)

                    distances_transformed = dist_transformed / num_segm * np.ones(num_segm)
                    distances_bt = np.array(
                        [np.linalg.norm([x_vals[i] - x_vals[i - 1], y_vals[i] - y_vals[i - 1], z_vals[i] - z_vals[i - 1]])
                         for i in range(1, num_segm + 1)])

                    row = self.insert_Z(row, z_vals[0])
                    row = self.replace_E(row, num_segm, 1, 1 * np.cos(cone_angle_rad))
                    replacement_rows = ''
                    for j in range(0, num_segm):
                        single_row = re.sub(pattern_X, 'X' + str(round(x_vals[j + 1], 3)), row)
                        single_row = re.sub(pattern_Y, 'Y' + str(round(y_vals[j + 1], 3)), single_row)
                        single_row = re.sub(pattern_Z, 'Z' + str(round(z_vals[j + 1], 3)), single_row)
                        single_row = self.replace_E(single_row, distances_transformed[j], distances_bt[j], 1)
                        replacement_rows = replacement_rows + single_row
                    row = replacement_rows

                    if update_x:
                        x_old = x_new
                        update_x = False
                    if update_y:
                        y_old = y_new
                        update_y = False

                    new_data.append(row)

        return new_data

    def translate_data(self, data, translate_x, translate_y, z_desired, e_parallel, e_perpendicular):
        new_data = []
        pattern_X = r'X[-0-9]*[.]?[0-9]*'
        pattern_Y = r'Y[-0-9]*[.]?[0-9]*'
        pattern_Z = r'Z[-0-9]*[.]?[0-9]*'
        pattern_E = r'E[-0-9]*[.]?[0-9]*'
        pattern_G = r'\AG[1] '
        z_initialized = False
        u_val = 0.0
        z_min = 0

        for row in data:
            g_match = re.search(pattern_G, row)
            z_match = re.search(pattern_Z, row)
            e_match = re.search(pattern_E, row)
            if g_match is not None and z_match is not None and e_match is not None:
                z_val = float(z_match.group(0).replace('Z', ''))
                if not z_initialized:
                    z_min = z_val
                    z_initialized = True
                if z_val < z_min:
                    z_min = z_val
        z_translate = z_desired - z_min

        for row in data:
            x_match = re.search(pattern_X, row)
            y_match = re.search(pattern_Y, row)
            z_match = re.search(pattern_Z, row)
            g_match = re.search(pattern_G, row)

            if g_match is None:
                new_data.append(row)
            else:
                if x_match is not None:
                    x_val = round(float(x_match.group(0).replace('X', '')) + translate_x - (e_parallel * np.cos(u_val)) + (e_perpendicular * np.sin(u_val)), 3)
                    row = re.sub(pattern_X, 'X' + str(x_val), row)
                if y_match is not None:
                    y_val = round(float(y_match.group(0).replace('Y', '')) + translate_y - (e_parallel * np.sin(u_val)) - (e_perpendicular * np.cos(u_val)), 3)
                    row = re.sub(pattern_Y, 'Y' + str(y_val), row)
                if z_match is not None:
                    z_val = max(round(float(z_match.group(0).replace('Z', '')) + z_translate, 3), z_desired)
                    row = re.sub(pattern_Z, 'Z' + str(z_val), row)
                new_data.append(row)

        return new_data

    def backtransform_file(self, path, output_path, cone_type, maximal_length, x_shift, y_shift, cone_angle_deg, z_desired, e_parallel, e_perpendicular):
        cone_angle_rad = cone_angle_deg / 180 * np.pi
        
        # 1. Backtransform Radiale
        with open(path, 'r') as f_gcode:
            data = f_gcode.readlines()
        data_bt = self.backtransform_data_radial(data, cone_type, maximal_length, cone_angle_rad)
        
        # 2. Traslazione
        data_bt_string = ''.join(data_bt)
        data_bt = [row + ' \n' for row in data_bt_string.split('\n')]
        data_bt = self.translate_data(data_bt, x_shift, y_shift, z_desired, e_parallel, e_perpendicular)
        
        # 3. Salvataggio
        data_bt_string = ''.join(data_bt)
        print(f"Salvataggio file in: {output_path}")
        with open(output_path, 'w+') as f_gcode_bt:
            f_gcode_bt.write(data_bt_string)
        print('File successfully backtransformed and translated.')

    def start(self):
        starttime = time.time()
        
        # Generazione percorso output automatico se non specificato esternamente
        path_input = self.get_file_name()
        if self._folder_name:
            # Se abbiamo settato una cartella output specifica
            base_name = os.path.basename(path_input)
            name_no_ext = os.path.splitext(base_name)[0]
            new_name = f"{name_no_ext}_backtransformed.gcode"
            output_path = os.path.join(self._folder_name, new_name)
        else:
            # Fallback (nella stessa cartella dell'input)
            output_path = path_input.replace(".gcode", "_backtransformed.gcode")

        self.backtransform_file(
            path=path_input,
            output_path=output_path,
            cone_type=self._cone_type,
            maximal_length=0.5,
            x_shift=self._x_shift,
            y_shift=self._y_shift,
            cone_angle_deg=self._cone_angle,
            z_desired=self._first_layer_height,
            e_parallel=0,
            e_perpendicular=0
        )
        endtime = time.time()
        print('GCode translated, time used:', endtime - starttime)