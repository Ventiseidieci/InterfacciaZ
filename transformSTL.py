import numpy as np
from stl import mesh
import time

#-----------------------------------------------------------------------------------------
# Transformation Settings
#-----------------------------------------------------------------------------------------

FILE_NAME = 'tower_01_-20'                       # Filename without extension
FOLDER_NAME_UNTRANSFORMED = 'stl/'
FOLDER_NAME_TRANSFORMED = 'stl_transformed/'    # Make sure this folder exists
CONE_ANGLE = 16                                 # Transformation angle
REFINEMENT_ITERATIONS = 1                       # refinement iterations of the stl. 2-3 is a good start for regular stls. If its already uniformaly fine, use 0 or 1. High number cause huge models and long script runtimes
TRANSFORMATION_TYPE = 'outward'                 # type of the cone: 'inward' & 'outward'

class stlTransformer():
     
     def __init__(self, cone_angle = 16, refinement_iterations=1, transformation_type = 'outward', folder_name_transformed='stl_transformed/'):
          self.file_name = None
          self.folder_name_utransformed = None
          self.folder_name_transformed = folder_name_transformed
          self.cone_angle = cone_angle
          self.refinement_iterations = refinement_iterations
          self.transformation_type = transformation_type
     
     def set_file_name(self, file_name):
          self.file_name = file_name

     def get_file_name(self):
          return self.file_name

     # Setter and Getter for folder_name_utransformed
     def set_folder_name_utransformed(self, folder_name_utransformed):
          self.folder_name_utransformed = folder_name_utransformed

     def get_folder_name_utransformed(self):
          return self.folder_name_utransformed

     # Setter and Getter for folder_name_transformed
     def set_folder_name_transformed(self, folder_name_transformed):
          self.folder_name_transformed = folder_name_transformed

     def get_folder_name_transformed(self):
          return self.folder_name_transformed

     # Setter and Getter for cone_angle
     def set_cone_angle(self, cone_angle):
          self.cone_angle = cone_angle

     def get_cone_angle(self):
          return self.cone_angle

     # Setter and Getter for refinement_iterations
     def set_refinement_iterations(self, refinement_iterations):
          self.refinement_iterations = refinement_iterations

     def get_refinement_iterations(self):
          return self.refinement_iterations

     # Setter and Getter for transformation_type
     def set_transformation_type(self, transformation_type):
          self.transformation_type = transformation_type

     def get_transformation_type(self):
          return self.transformation_type
   
     def transformation_kegel(self, points, cone_angle_rad, cone_type):
          """
          Computes the cone-transformation (x', y', z') = (x / cos(angle), y / cos(angle), z + \sqrt{x^{2} + y^{2}} * tan(angle))
          for a list of points
          :param points: array
                  array of points of shape ( , 3)
            :param cone_type: string
             String, either 'outward' or 'inward', defines which transformation should be used
         :return: array
             array of transformed points, of same shape as input array
         """
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
          """
          Compute a refinement of a triangle. On every side, the midpoint is added. The three corner points and three
          midpoints result in four smaller triangles.
          :param triangle: array
               array of three points of shape (3, 3) (one triangle)
          :return: array
               array of shape (4, 3, 3) of four triangles
          """
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
          """
          Compute a refinement of a triangulation using the refinement_four_triangles function.
          The number of iteration defines, how often the triangulation has to be refined; n iterations lead to
          4^n times many triangles.
          :param triangle_array: array
               array of shape (num_triangles, 3, 3) of triangles
          :param num_iterations: int
          :return: array
               array of shape (num_triangles*4^num_iterations, 3, 3) of triangles
          """
          refined_array = triangle_array
          for i in range(0, num_iterations):
               n_triangles = refined_array.shape[0]*4
               refined_array = np.array(list(map(self.refinement_four_triangles, refined_array)))
               refined_array = np.reshape(refined_array, (n_triangles, 3, 3))
          return refined_array


     def transformation_STL_file(self, path, cone_type, cone_angle_deg, nb_iterations):
          """
          Read a stl-file, refine the triangulation and transform it according to the cone-transformation
          :param path: string
               path to the stl file
          :param cone_type: string
               String, either 'outward' or 'inward', defines which transformation should be used
          :param cone_angle: int
               angle to transform the part
          :param nb_iterations: int
               number of iterations, the triangulation should be refined before the transformation
          :return: mesh object
               transformed triangulation as mesh object which can be stored as stl file
          """
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
          transformed_STL = self.transformation_STL_file(path=self.get_file_name(), cone_type=self.get_transformation_type(), cone_angle_deg=self.get_cone_angle(), nb_iterations=self.get_refinement_iterations())
          transformed_STL.save(self.get_folder_name_transformed() + name + '_' + self.get_transformation_type() + '_' + str(self.get_cone_angle()) + 'deg_transformed.stl')
          endzeit = time.time()
          print('Transformation time:', endzeit - startzeit)