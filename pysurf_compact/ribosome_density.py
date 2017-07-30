import math
import numpy as np
from scipy import spatial
from datetime import datetime
from graph_tool.all import Graph

import graphs
import pysurf_io as io


# Reads in a mask from file.
def read_in_mask(mask_file):
    print '\nReading in the mask %s' % mask_file
    mask = io.load_tomo(mask_file)
    print 'Shape and data type:'
    print mask.shape
    print mask.dtype
    return mask


# Returns a list of foreground voxels as tupels in form (x, y, z) from a binary mask (numpy ndarray).
def get_foreground_voxels_from_mask(mask):
    voxels = []
    if isinstance(mask, np.ndarray):
        # check that the mask is a 3D array:
        assert(len(mask.shape) == 3)
        indices = mask.nonzero()
        voxels_num = indices[0].size
        for i in xrange(voxels_num):
            voxel_i = (indices[0][i], indices[1][i], indices[2][i])
            voxels.append(voxel_i)
    else:
        print 'Error: Wrong input data type, the mask has to be a numpy ndarray (3D).'
        exit(1)
    return voxels


# Rescales foreground voxels coordinates from a mask file using the scaling factor inside a new mask with the given shape.
def rescale_mask(in_mask_file, out_mask_file, scaling_factor, out_shape):
    in_mask = read_in_mask(in_mask_file)
    in_target_voxels = get_foreground_voxels_from_mask(in_mask)

    out_mask = np.zeros(out_shape, dtype=np.uint8)

    for in_voxel in in_target_voxels:
        in_x = in_voxel[0]
        in_y = in_voxel[1]
        in_z = in_voxel[2]
        out_x = math.floor(in_x * scaling_factor)
        out_y = math.floor(in_y * scaling_factor)
        out_z = math.floor(in_z * scaling_factor)
        out_mask[out_x, out_y, out_z] = 1

    io.save_numpy(out_mask, out_mask_file)


# Returns a list of foreground voxels as tupels in form (x, y, z) from a numpy ndarray in format [[x1,y1,z1], [x2,y2,z2], ...].
def ndarray_voxels_to_tupel_list(voxels_ndarray):
    tupel_list = []
    if isinstance(voxels_ndarray, np.ndarray):
        # check that voxels_ndarray is a 2D array with 3 columns:
        dims = voxels_ndarray.shape
        assert (len(dims) == 2)
        assert (dims[1] == 3)
        voxels_list = voxels_ndarray.tolist()
        for voxel in voxels_list:
            x = voxel[0]
            y = voxel[1]
            z = voxel[2]
            tupel_list.append((x, y, z))
    else:
        print 'Error: Wrong input data type, the voxels have to be given as a numpy ndarray.'
        exit(1)
    return tupel_list


# From a list of foreground voxels as tupels in form (x, y, z), returns a numpy ndarray in format [[x1,y1,z1], [x2,y2,z2], ...].
def tupel_list_to_ndarray_voxels(tupel_list):
    voxels_list = []
    for tupel in tupel_list:
        x = tupel[0]
        y = tupel[1]
        z = tupel[2]
        voxels_list.append([x, y, z])
    voxels_ndarray = np.array(voxels_list)
    # check that voxels_ndarray is a 2D array with 3 columns:
    dims = voxels_ndarray.shape
    assert (len(dims) == 2)
    assert (dims[1] == 3)
    return voxels_ndarray


# Gets the target voxels from the ribosome mask and pre-filters them to those that are inside the membrane mask
# (value 1), printing out the voxel numbers and, if verbose, the voxels. Returns the pre-filtered set as a list.
def get_target_voxels_in_membrane_mask(ribo_mask, mem_mask, verbose=False):
    if isinstance(ribo_mask, np.ndarray) and isinstance(mem_mask, np.ndarray):
        assert (ribo_mask.shape == mem_mask.shape)  # both mask have to have the same dimensions and scales
        # Find the set of voxels of ribosome centers mapped on the membrane, called 'target voxels' from now on:
        target_voxels = get_foreground_voxels_from_mask(ribo_mask)
        print '%s target voxels' % len(target_voxels)
        if verbose:
            print target_voxels

        target_voxels_in_membrane_mask = []
        for target_voxel in target_voxels:
            if mem_mask[target_voxel[0], target_voxel[1], target_voxel[2]] == 1:
                target_voxels_in_membrane_mask.append(target_voxel)
            else:
                print 'Warning: Target voxel (%s, %s, %s) not inside the membrane!' % (target_voxel[0], target_voxel[1], target_voxel[2])
        print '%s target voxels in membrane' % len(target_voxels_in_membrane_mask)
        if verbose:
            print target_voxels_in_membrane_mask
        return target_voxels_in_membrane_mask
    else:
        print 'Error: Wrong input data type, the both masks have to be numpy ndarrays.'
        exit(1)


# Extracts coordinates of all particles from a motive list EM file and returns them in numpy array format.
# Scales the coordinates with the given scaling factor by multiplying (default 1 = no scaling).
def particles_xyz_to_np_array(motl_em_file, scaling_factor=1):
    motl = io.load_tomo(motl_em_file)
    particles_xyz = []
    for col in xrange(motl.shape[1]):
        x = scaling_factor * motl[7, col, 0]
        y = scaling_factor * motl[8, col, 0]
        z = scaling_factor * motl[9, col, 0]
        particles_xyz.append([x, y, z])
    particles_xyz = np.array(particles_xyz)
    return particles_xyz


# Finds for each particle coordinates the nearest vertex coordinates (both given by an array) within a given radius.
# If no vertex exists within the radius, [-1, -1, -1] is returned at the respective index.
# Note: all input parameters have to be in the same scale (either in pixels or in nm)!
# Uses KD trees for a fast search. Returns a numpy array with the nearest vertices coordinates.
def nearest_vertex_for_particles(vertices_xyz, particles_xyz, radius):
    # Construct the KD tree from the vertices coordinates:
    tree = spatial.KDTree(vertices_xyz)
    # Search in the tree for the nearest vertex within the radius to the particles:
    (distances, nearest_treedata_positions) = tree.query(particles_xyz, distance_upper_bound=radius)
    # defaults: k=1 number of nearest neighbors, eps=0 precise distance, p=2 Euclidean distance
    nearest_vertices_xyz = []
    for i in nearest_treedata_positions:
        if i < len(vertices_xyz):
            nearest_vertices_xyz.append(tree.data[i])
        else:
            nearest_vertices_xyz.append([-1, -1, -1])
    nearest_vertices_xyz = np.array(nearest_vertices_xyz)
    return nearest_vertices_xyz


# Class defining the VoxelGraph object, its attributes and methods.
class VoxelGraph(graphs.SegmentationGraph):
    # Builds a graph from a numpy ndarray mask with values 1 and 0, including only voxels with value 1.
    def build_graph_from_np_ndarray(self, mask, verbose):
        if isinstance(mask, np.ndarray):
            assert mask.shape == (self.scale_x, self.scale_y, self.scale_z)  # dimensions and scales of the mask have to be the same as given in the initialization method
            # Find the set of the membrane voxels, which become the vertices of the graph:
            membrane_voxels = get_foreground_voxels_from_mask(mask)
            print '%s membrane voxels' % len(membrane_voxels)
            if verbose:
                print membrane_voxels
            self.__expand_voxels(mask, membrane_voxels, verbose)
        else:
            print 'Error: Wrong input data type, the mask has to be a numpy ndarray.'
            exit(1)

    @staticmethod
    # Returns neighbor voxels of a voxel inside a matrix (mask), which have value 1 (foreground)
    def foreground_neighbors_of_voxel(mask, voxel):
        neighbor_voxels = []
        if isinstance(mask, np.ndarray):
            if isinstance(voxel, tuple) and (len(voxel) == 3):
                x = voxel[0]
                y = voxel[1]
                z = voxel[2]
                x_size = mask.shape[0]
                y_size = mask.shape[1]
                z_size = mask.shape[2]
                # iterate over all possible (max 26) neighbor voxels combinations
                for i in (x - 1, x, x + 1):
                    for j in (y - 1, y, y + 1):
                        for k in (z - 1, z, z + 1):
                            # do not add the voxel itself and voxels outside the border
                            if ((i, j, k) != (x, y, z)) and \
                                    (i in xrange(0, x_size)) and (j in xrange(0, y_size)) and (k in xrange(0, z_size)):
                                # add only foreground voxels to the neighbors list
                                if mask[i, j, k] == 1:
                                    neighbor_voxels.append((i, j, k))
            else:
                print 'Error: Wrong input data, the voxel has to be a tuple of integers of length 3.'
                exit(1)
        else:
            print 'Error: Wrong input data type, the mask has to be a numpy ndarray.'
            exit(1)
        return neighbor_voxels

    # An iterative function used for building the membrane graph. Expands each foreground voxel, adding it, its foreground
    # neighbor voxels and edges with euclidean distances between the neighbor voxels (all scaled in nm) to the graph.
    # This method should only be called by the method build_graph_from_np_ndarray!
    def __expand_voxels(self, mask, remaining_mem_voxels, verbose):
        while len(remaining_mem_voxels) > 0:
            try:
                if verbose:
                    print '%s remaining membrane voxels' % len(remaining_mem_voxels)
                elif len(remaining_mem_voxels) % 1000 == 0:
                    now = datetime.now()
                    print '%s remaining membrane voxels on: %s-%s-%s %s:%s:%s' \
                          % (len(remaining_mem_voxels), now.year, now.month, now.day,
                             now.hour, now.minute, now.second)

                # get and remove the last voxel on the list of remaining membrane voxels to expand it next
                voxel_to_expand = remaining_mem_voxels.pop()
                if verbose:
                    print '\nCurrent voxel to expand:'
                    print voxel_to_expand

                scaled_voxel_to_expand = (voxel_to_expand[0] * self.scale_factor_to_nm, voxel_to_expand[1] * self.scale_factor_to_nm, voxel_to_expand[2] * self.scale_factor_to_nm)
                # If the scaled voxel to be expanded has been already added to the graph, get its vertex descriptor:
                if scaled_voxel_to_expand in self.coordinates_to_vertex_index:
                    v_expanded = self.graph.vertex(self.coordinates_to_vertex_index[scaled_voxel_to_expand])
                # Otherwise, add the scaled voxel to be expanded as vertex to the graph:
                else:
                    v_expanded = self.graph.add_vertex()
                    self.graph.vp.xyz[v_expanded] = [scaled_voxel_to_expand[0], scaled_voxel_to_expand[1], scaled_voxel_to_expand[2]]
                    self.coordinates_to_vertex_index[scaled_voxel_to_expand] = self.graph.vertex_index[v_expanded]
                    if verbose:
                        print 'This voxel has been added to the graph as vertex.'

                # Get the neighbor membrane voxels of the current voxel:
                neighbor_voxels = self.foreground_neighbors_of_voxel(mask, voxel_to_expand)

                # If there is at least one foreground neighbor, do for each:
                if len(neighbor_voxels) > 0:
                    for neighbor_voxel in neighbor_voxels:

                        scaled_neighbor_voxel = (neighbor_voxel[0] * self.scale_factor_to_nm, neighbor_voxel[1] * self.scale_factor_to_nm, neighbor_voxel[2] * self.scale_factor_to_nm)
                        # If the scaled neighbor voxel has been already added to the graph, get its vertex descriptor:
                        if scaled_neighbor_voxel in self.coordinates_to_vertex_index:
                            v_neighbor = self.graph.vertex(self.coordinates_to_vertex_index[scaled_neighbor_voxel])
                        # Otherwise, add the neighbor voxel as vertex to the graph:
                        else:
                            v_neighbor = self.graph.add_vertex()
                            self.graph.vp.xyz[v_neighbor] = [scaled_neighbor_voxel[0], scaled_neighbor_voxel[1], scaled_neighbor_voxel[2]]
                            self.coordinates_to_vertex_index[scaled_neighbor_voxel] = self.graph.vertex_index[v_neighbor]
                            if verbose:
                                print 'The neighbor voxel (%s, %s, %s) has been added to the graph as a vertex.' \
                                      % (neighbor_voxel[0], neighbor_voxel[1], neighbor_voxel[2])

                        # Add an edge with a distance between the expanded scaled vertex and the scaled neighbor vertex, if it does not exist yet:
                        if not (((scaled_voxel_to_expand, scaled_neighbor_voxel) in self.coordinates_pair_connected) or ((scaled_neighbor_voxel, scaled_voxel_to_expand) in self.coordinates_pair_connected)):
                            ed = self.graph.add_edge(v_expanded, v_neighbor)  # edge descriptor
                            self.graph.ep.distance[ed] = self.distance_between_voxels(scaled_voxel_to_expand, scaled_neighbor_voxel)
                            self.coordinates_pair_connected[(scaled_voxel_to_expand, scaled_neighbor_voxel)] = True
                            if verbose:
                                print 'The neighbor voxels (%s, %s, %s) and (%s, %s, %s) have been connected by an edge with a distance of %s pixels.' \
                                      % (voxel_to_expand[0], voxel_to_expand[1], voxel_to_expand[2],
                                         neighbor_voxel[0], neighbor_voxel[1], neighbor_voxel[2],
                                         self.graph.ep.distance[ed])
            except Exception, exc:
                print "An exception happened: " + str(exc)
                print 'There were %s remaining membrane voxels.' % len(remaining_mem_voxels)
        else:
            if verbose:
                print '0 remaining membrane voxels'

    # Fills the dictionary coordinates_to_vertex_index. To use after reading a graph from a file before density calculation.
    def fill_coordinates_to_vertex_index(self):
        for v in self.graph.vertices():
            voxel = self.graph.vp.xyz[v]
            voxel = (voxel[0], voxel[1], voxel[2])
            if voxel not in self.coordinates_to_vertex_index:
                self.coordinates_to_vertex_index[voxel] = self.graph.vertex_index[v]
