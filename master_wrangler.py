#!/usr/bin/env python
# -*- coding: utf-8 -*-
## This python script loads the osm format data, extracts the relevant information
#in a clean format

import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
from string import join

import cerberus

import schema

OSM_PATH = "miami_florida.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
postcode_type_re = re.compile(r'3\d\d\d\d')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

mapping = { "St": "Street",
            "St.": "Street",
            "Ave": "Avenue",
            "Rd.": "Road", "Rd": "Road",
            "Pl": "Place",  "Pl.": "Place",
            "Trl": "Trail", "Ln": "Lane",
            "Dr": "Drive", "Dr.": "Drive",
            "Ct": "Court", "Ct.": "Court",
            "Cir": "Circle", "Ter": "Terrace"
            }



def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML element to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    # YOUR CODE HERE
    if element.tag == 'node':
        for items in node_attr_fields:
            node_attribs[items] = element.attrib[items]
        #tag_dict = {}
        for tag in element.iter("tag"):
            tag_dict = {"id":None, "key":None, "value":None, "type":None}
            if re.search(PROBLEMCHARS, tag.attrib["k"]):
                continue
            elif re.search(LOWER_COLON, tag.attrib["k"]):
                key_value = tag.attrib["k"].split(":",1)
                #print key_value[0], key_value[1]
                tag_dict["id"] = node_attribs["id"]
                tag_dict["key"] = key_value[1]
                ### update the abbreviated street names
                tag_dict["value"] = tag.attrib["v"]
                if tag.attrib["k"] == "addr:street" :
                    fields = tag.attrib["v"].split()
                    for order in mapping:
                        if order == fields[-1]:
                            fields[-1] = mapping[order]
                            tag_dict["value"] = join(fields," ")
                ### Fix postal code values format
                if tag.attrib["k"] == "addr:postcode" :
                    mo = postcode_type_re.search(tag.attrib["v"])
                    if mo:
                        tag_dict["value"] = mo.group()
                tag_dict["type"] = key_value[0]
                tags.append(tag_dict)
            else:
                tag_dict["id"] = node_attribs["id"]
                tag_dict["key"] = tag.attrib["k"]
                tag_dict["value"] = tag.attrib["v"]
                tag_dict["type"] = default_tag_type
                tags.append(tag_dict)
        #pprint.pprint(tags)
        return {'node': node_attribs, 'node_tags': tags}

    elif element.tag == 'way':
        for items in way_attr_fields:
            way_attribs[items] = element.attrib[items]
        position_count = 0
        for tag in element.iter("nd"):
            way_dict = {"id":None, "node_id":None, "position":None}
            way_dict["id"] = way_attribs["id"]
            way_dict["node_id"] = tag.attrib["ref"]
            way_dict["position"] = position_count
            way_nodes.append(way_dict)
            position_count += 1
        #pprint.pprint(way_nodes)
        for tag in element.iter("tag"):
            tag_dict = {"id":None, "key":None, "value":None, "type":None}
            if re.search(PROBLEMCHARS, tag.attrib["k"]):
                continue
            elif re.search(LOWER_COLON, tag.attrib["k"]):
                key_value = tag.attrib["k"].split(":",1)
                #print key_value[0], key_value[1]
                tag_dict["id"] = way_attribs["id"]
                tag_dict["key"] = key_value[1]
                tag_dict["value"] = tag.attrib["v"]
                ### update the abbreviated street names
                if tag.attrib["k"] == "addr:street" :
                    fields = tag.attrib["v"].split()
                    for order in mapping:
                        if order == fields[-1]:
                            fields[-1] = mapping[order]
                            tag_dict["value"] = join(fields," ")
                ### Fix postal code values format
                if tag.attrib["k"] == "addr:postcode" :
                    mo = postcode_type_re.search(tag.attrib["v"])
                    if mo:
                        tag_dict["value"] = mo.group()
                tag_dict["type"] = key_value[0]
                tags.append(tag_dict)
            else:
                tag_dict["id"] = way_attribs["id"]
                tag_dict["key"] = tag.attrib["k"]
                tag_dict["value"] = tag.attrib["v"]
                tag_dict["type"] = default_tag_type
                tags.append(tag_dict)

        #pprint.pprint(tags)
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)

        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=True)
