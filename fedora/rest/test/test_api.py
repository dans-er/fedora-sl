#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import unittest

import logging

import sys

from fedora.rest.api import Fedora

connection_parameter_file = "teasy.csv"
test_file = "easy-file:219890"


class TestFedora(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cfg_file = os.path.join(os.path.expanduser("~"), "src", connection_parameter_file)
        with open(cfg_file) as cfg:
            line = cfg.readline()
        host, port, username, password = line.split(",")
        if not host.startswith("http"):
            host = "http://" + host
        cls.fedora = Fedora(host, port, username, password)

        # set up logging
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        ch.setFormatter(formatter)
        root.addHandler(ch)

    def test_object_xml(self):
        objectxml = self.fedora.object_xml(test_file)
        #print(objectxml)
        self.assertTrue(objectxml.startswith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"))

    def test_datastream_rels_ext(self):
        datastream = self.fedora.datastream(test_file, "RELS-EXT")
        #print(datastream)
        self.assertTrue("<rdf:RDF xmlns:rdf=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\">" in datastream)

    def test_datastream_easy_file_metadata(self):
        datastream = self.fedora.datastream(test_file, "EASY_FILE_METADATA", content_format="xml")
        #print(datastream)
        self.assertTrue(datastream.startswith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"))

    def test_datastream_easy_file_metadata_content(self):
        datastream = self.fedora.datastream(test_file, "EASY_FILE_METADATA")
        #print(datastream)
        self.assertTrue("<fimd:file-item-md" in datastream)

    def test_datastream_easy_file(self):
        datastream = self.fedora.datastream(test_file, "EASY_FILE", content_format="xml")
        print(datastream)
        self.assertTrue(datastream.startswith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"))

    def test_add_relationship(self):
        self.fedora.add_relationship(test_file,
                                     "http://dans.knaw.nl/ontologies/conversions#isConversionOf",
                                     "info:fedora/easy-file:2")
        self.fedora.add_relationship(test_file,
                                     "http://dans.knaw.nl/ontologies/conversions#isConvertedBy",
                                     "http://example-archive.org/aips/55e73f76-5b10-11e6-9822-685b357e70b6.5")
        self.fedora.add_relationship(test_file,
                                     "http://dans.knaw.nl/ontologies/conversions#conversionDate",
                                     "2016-11-23T00:00:00.000Z", is_literal=True,
                                     data_type="http://www.w3.org/2001/XMLSchema#dateTime")

    def test_purge_relationship(self):
        self.fedora.purge_relationship(test_file,
                                       "http://dans.knaw.nl/ontologies/conversions#isConversionOf",
                                       "info:fedora/easy-file:2")
        self.fedora.purge_relationship(test_file,
                                       "http://dans.knaw.nl/ontologies/conversions#isConvertedBy",
                                       "http://example-archive.org/aips/55e73f76-5b10-11e6-9822-685b357e70b6.5")
        self.fedora.purge_relationship(test_file,
                                       "http://dans.knaw.nl/ontologies/conversions#conversionDate",
                                       "2016-11-23T00:00:00.000Z", is_literal=True,
                                       data_type="http://www.w3.org/2001/XMLSchema#dateTime")