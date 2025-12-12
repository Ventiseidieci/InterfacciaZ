import numpy as np
from stl import mesh
import time
import os

class stlTransformer():
     
     def __init__(self, cone_angle = 16, refinement_iterations=1, transformation_type = 'outward'):
          self.file_name = None
          self.folder_name_transformed = 'stl_transformed/' # Default, ma sovrascrivibile
          self.cone_angle = cone_angle
          self.refinement_iterations = refinement_iterations
          self.transformation_type = transformation_type
     
     def set_file_name(self, file_name):
          self.file_name = file_name

     def set_folder_name_transformed(self, folder_name_transformed):
          self.folder_name_transformed = folder_name_transformed

     def get_folder_name_transformed(self):
          return self.folder_name_transformed

     # ... (Metodi getter/setter opzionali rimossi per brevità, usa accesso diretto o lasciali se preferisci) ...
     # Se vuoi tenere i vecchi getter/setter, incollali qui. Quelli essenziali sono sopra.

     def transformation_kegel(self, points, cone_angle_rad, cone_type):
          if cone_type == 'outward':
               c = 1
          elif cone_type == 'inward':
               c = -1
          else:
               raise ValueError('{} is not a admissible type for the transformation'.format(cone_type))
          f = (lambda x, y, z: np.array([x/np.cos(cone_angle_rad), y/np.cos(cone_angle_rad), z + c * np.sqrt(x**2 + y**2)*np.tan(cone_angle_rad)]))
          points_transformed = list(map(f, points[:, 0], points[:, 1], points[:, 2]))
          return np.array(points_transformed)

     def refinement_four_triangles(self, triangle):
          point1 = triangle[0]
          point2 = triangle[1]
          point3 = triangle[2]
          midpoint12 = (point1 + point2) / 2
          midpoint23 = (point2 + point3) / 2
          midpoint31 = (point3 + point1) / 2
          triangle1 = np.array([point1, midpoint12, midpoint31])
          triangle2 = np.array([point2, midpoint23, midpoint12])
          triangle3 = np.array([point3, midpoint31, midpoint23])
          triangle4 = np.array([midpoint12, midpoint23, midpoint31])
          return np.array([triangle1, triangle2, triangle3, triangle4])

     def refinement_triangulation(self, triangle_array, num_iterations):
          refined_array = triangle_array
          for i in range(0, num_iterations):
               n_triangles = refined_array.shape[0]*4
               refined_array = np.array(list(map(self.refinement_four_triangles, refined_array)))
               refined_array = np.reshape(refined_array, (n_triangles, 3, 3))
          return refined_array

     def transformation_STL_file(self, path, cone_type, cone_angle_deg, nb_iterations):
          cone_angle_rad = cone_angle_deg / 180 * np.pi
          my_mesh = mesh.Mesh.from_file(path)
          vectors = my_mesh.vectors
          vectors_refined = self.refinement_triangulation(vectors, nb_iterations)
          vectors_refined = np.reshape(vectors_refined, (-1, 3))
          vectors_transformed = self.transformation_kegel(vectors_refined, cone_angle_rad, cone_type)
          vectors_transformed = np.reshape(vectors_transformed, (-1, 3, 3))
          my_mesh_transformed = np.zeros(vectors_transformed.shape[0], dtype=mesh.Mesh.dtype)
          my_mesh_transformed['vectors'] = vectors_transformed
          my_mesh_transformed = mesh.Mesh(my_mesh_transformed)
          return my_mesh_transformed

     def start(self, name):
          startzeit = time.time()
          transformed_STL = self.transformation_STL_file(path=self.file_name, cone_type=self.transformation_type, cone_angle_deg=self.cone_angle, nb_iterations=self.refinement_iterations)
          
          # Costruisce il percorso completo
          output_filename = f"{name}_{self.transformation_type}_{self.cone_angle}deg_transformed.stl"
          full_output_path = os.path.join(self.folder_name_transformed, output_filename)
          
          transformed_STL.save(full_output_path)
          endzeit = time.time()
          print('Transformation time:', endzeit - startzeit)
          return full_output_path # Ritorna il percorso per usarlo dopo