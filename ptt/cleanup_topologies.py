
"""
    Copyright (C) 2019 The University of Sydney, Australia
    
    This program is free software; you can redistribute it and/or modify it under
    the terms of the GNU General Public License, version 2, as published by
    the Free Software Foundation.
    
    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
    for more details.
    
    You should have received a copy of the GNU General Public License along
    with this program; if not, write to Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""


##################################################################################################
# Clean up topologies, including:                                                                #
#   * Removing any regular features not referenced by topologies.                                #
#   * Restricting the time periods of referenced features to match the referencing topologies.   #
##################################################################################################


from __future__ import print_function
import sys
import math
import pygplates


# Required pygplates version.
# Need ability to query topological sections.
PYGPLATES_VERSION_REQUIRED = pygplates.Version(21)


def remove_features_not_referenced_by_topologies(
        feature_collections):
    # Docstring in numpydoc format...
    """Remove any regular features not referenced by topological features.
    
    The results are returned as a list of pygplates.FeatureCollection (one per input feature collection).
    
    The input feature collections should contain the topological and regular features that make up the topological model.
    Ensure you at least specify all topological features in the topological model, otherwise regular features
    referenced by the missing topologies will get removed.
    
    Parameters
    ----------
    feature_collections : sequence of (str, or sequence of pygplates.Feature, or pygplates.FeatureCollection, or pygplates.Feature)
        A sequence of feature collections containing both the topological features and the regular features they reference.
        Each collection in the sequence can be a filename, or a sequence (eg, list of tuple) or features, or
        a feature collection, or even a single feature.
    
    Returns
    -------
    list of pygplates.FeatureCollection
        The (potentially) modified feature collections.
        Returned list is same length as ``feature_collections``.
    """
    
    # Convert each feature collection into a list of features so we can more easily remove features
    # and insert features at arbitrary locations within each feature collection
    # (for example removing an unreferenced regular feature).
    feature_collections = [list(pygplates.FeatureCollection(feature_collection))
        for feature_collection in feature_collections]
    
    # Set of feature IDs of all topological features to keep (that should not be removed).
    topology_feature_ids = set()
    
    property_delegates_visitor = _GetTopologicalPropertyDelegatesVisitor()
    for feature_collection in feature_collections:
        for feature in feature_collection:
            for property in feature:
                # Get the top-level property value (containing all times) not just a specific time.
                property_value = property.get_time_dependent_value()
                # If we visited a topological line, polygon or network then add the current feature
                # as a topological feature and continue to the next feature.
                if property_delegates_visitor.visit_property_value(property_value):
                    topology_feature_ids.add(feature.get_feature_id())
                    break
    
    # Set of feature IDs of all feature referenced by topologies.
    referenced_feature_ids = set(property_delegate.get_feature_id()
        for property_delegate in property_delegates_visitor.get_topological_property_delegates())
    
    # Remove any features that are not topological and have not been referenced by a topology.
    for feature_collection in feature_collections:
        feature_index = 0
        while feature_index < len(feature_collection):
            feature = feature_collection[feature_index]
            feature_id = feature.get_feature_id()
            if (feature_id not in topology_feature_ids and
                feature_id not in referenced_feature_ids):
                del feature_collection[feature_index]
                feature_index -= 1
            
            feature_index += 1
    
    # Return our (potentially) modified feature collections as a list of pygplates.FeatureCollection.
    return [pygplates.FeatureCollection(feature_collection)
        for feature_collection in feature_collections]


# Private helper class (has '_' prefix) to find topology-related GpmlPropertyDelegate's.
class _GetTopologicalPropertyDelegatesVisitor(pygplates.PropertyValueVisitor):
    def __init__(self):
        super(_GetTopologicalPropertyDelegatesVisitor, self).__init__()
        self.topological_property_delegates = []
    
    def get_topological_property_delegates(self):
        return self.topological_property_delegates
    
    def visit_property_value(self, property_value):
        """Visit a property value.
        
        Return True if visited a topological line, polygon or network."""
        num_topological_property_delegates_before_visit = len(self.topological_property_delegates)
        property_value.accept_visitor(self)
        
        return len(self.topological_property_delegates) > num_topological_property_delegates_before_visit
    
    def visit_gpml_constant_value(self, gpml_constant_value):
        # Visit the GpmlConstantValue's nested property value.
        gpml_constant_value.get_value().accept_visitor(self)
    
    def visit_gpml_piecewise_aggregation(self, gpml_piecewise_aggregation):
        # Only need to visit if contains a topological line, polygon or network.
        value_type = gpml_piecewise_aggregation.get_value_type()
        if (value_type == pygplates.GpmlTopologicalLine or
            value_type == pygplates.GpmlTopologicalPolygon or
            value_type == pygplates.GpmlTopologicalNetwork):
            # Visit the property value in each time window.
            for gpml_time_window in gpml_piecewise_aggregation:
                gpml_time_window.get_value().accept_visitor(self)
    
    def visit_gpml_topological_line(self, gpml_topological_line):
        # Topological line sections are topological sections (which contain a property delegate).
        for section in gpml_topological_line.get_sections():
            self.topological_property_delegates.append(section.get_property_delegate())
    
    def visit_gpml_topological_polygon(self, gpml_topological_polygon):
        # Topological polygon exterior sections are topological sections (which contain a property delegate).
        for exterior_section in gpml_topological_polygon.get_exterior_sections():
            self.topological_property_delegates.append(exterior_section.get_property_delegate())
    
    def visit_gpml_topological_network(self, gpml_topological_network):
        # Topological network boundary sections are topological sections (which contain a property delegate).
        for boundary_section in gpml_topological_network.get_boundary_sections():
            self.topological_property_delegates.append(boundary_section.get_property_delegate())
        # Topological network interiors are already property delegates.
        for interior in gpml_topological_network.get_interiors():
            self.topological_property_delegates.append(interior)


if __name__ == '__main__':
    
    import os.path
    
    
    # Check the imported pygplates version.
    if not hasattr(pygplates, 'Version') or pygplates.Version.get_imported_version() < PYGPLATES_VERSION_REQUIRED:
        print('{0}: Error - imported pygplates version {1} but version {2} or greater is required'.format(
                os.path.basename(__file__), pygplates.Version.get_imported_version(), PYGPLATES_VERSION_REQUIRED),
            file=sys.stderr)
        sys.exit(1)
    
    
    import argparse
    
    
    def main():
    
        __description__ = \
    """Remove any regular features not referenced by topological features.
    
    The input files should contain the topological and regular features that make up the topological model.
    Ensure you at least specify all topological features in the topological model, otherwise regular features
    referenced by the missing topologies will get removed.
    
    The results are written back to the input files unless an output filename prefix is provided.

    NOTE: Separate the positional and optional arguments with '--' (workaround for bug in argparse module).
    For example...

    python %(prog)s -o cleanup_topologies_ -- topologies.gpml
     """

        # The command-line parser.
        parser = argparse.ArgumentParser(description = __description__, formatter_class=argparse.RawDescriptionHelpFormatter)
        
        parser.add_argument('-o', '--output_filename_prefix', type=str,
                metavar='output_filename_prefix',
                help='Optional output filename prefix. If one is provided then an output file '
                    'is created for each input file by prefixing the input filenames. '
                    'If no filename prefix is provided then the input files are overwritten.')
        
        parser.add_argument('input_filenames', type=str, nargs='+',
                metavar='input_filename',
                help='One or more files containing topological features and features referenced by them.')
        
        # Parse command-line options.
        args = parser.parse_args()
        
        # Read the input feature collections.
        input_feature_collections = [pygplates.FeatureCollection(input_filename)
                for input_filename in args.input_filenames]
        
        # Remove features not referenced by topologies.
        output_feature_collections = remove_features_not_referenced_by_topologies(input_feature_collections)
        
        # Write the modified feature collections to disk.
        for feature_collection_index in range(len(output_feature_collections)):
            output_feature_collection = output_feature_collections[feature_collection_index]

            # Each output filename is the input filename with an optional prefix prepended.
            input_filename = args.input_filenames[feature_collection_index]
            if args.output_filename_prefix:
                dir, file_basename = os.path.split(input_filename)
                output_filename = os.path.join(dir, '{0}{1}'.format(args.output_filename_prefix, file_basename))
            else:
                output_filename = input_filename
            
            output_feature_collection.write(output_filename)
        
        sys.exit(0)
    
    import traceback
    
    try:
        main()
        sys.exit(0)
    except Exception as exc:
        print('ERROR: {0}'.format(exc), file=sys.stderr)
        # Uncomment this to print traceback to location of raised exception.
        # traceback.print_exc()
        sys.exit(1)