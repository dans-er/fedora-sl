#! /usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
import os
import re

import logging

from fedora import utils
from fedora.rest.api import Fedora
from fedora.rest.ds import DatastreamProfile, FileItemMetadata

LOG = logging.getLogger(__name__)


class Worker(object):
    """
    Do default chores with the fedora rest api.

    A worker reads and writes csv-files. The default dialect for such reading and writing is encapsulated in the
    class csv.excel. You can specify your own dialect by providing a class with the appropriate attributes.
    Example::

        class MyDialect(object):
            delimiter = ','
            quotechar = '"'
            escapechar = None
            doublequote = True
            skipinitialspace = False
            lineterminator = '\r\n'
            quoting = csv.QUOTE_MINIMAL

    """
    def __init__(self, dialect=csv.excel):
        self.fedora = Fedora()
        self.dialect = dialect

    def download_batch(self, id_list,
                       dump_dir="worker-downloads",
                       log_file="worker-log.csv",
                       id_in_path=True,
                       chunk_size=1024):
        """
        Download a bunch of files, store metadata in a work-log, compare checksums.

        :param id_list: either a list of file-id's or the name of the file that contains this list
        :param dump_dir: where to store downloaded files
        :param log_file: where to write the work-log
        :param dialect: what csv dialect should the work-log be written in, default: :class:`csv.excel`
        :param id_in_path: should (the number part of) the object_id be part of the local path, default: `True`
        :param chunk_size: size of chuncks for read-write operation, default: 1024
        :return: count of checksum errors
        """
        ds_id = "EASY_FILE"
        checksum_error_count = 0
        work_log = os.path.abspath(log_file)
        os.makedirs(os.path.dirname(work_log), exist_ok=True)
        with open(work_log, 'w', newline='') as csv_log:
            csv_writer = csv.writer(csv_log, dialect=self.dialect)
            csv_writer.writerow(["object_id", "ds_id", "server_date", "filename", "path", "local_path",
                                 "media_type", "size",
                                 "checksum_type", "checksum", "creation_date",
                                 "creator_role", "visible_to", "accessible_to",
                                 "checksum_error"])

            for object_id in self.id_iter(id_list):
                meta = self.fedora.download(object_id, ds_id, dump_dir, id_in_path, chunk_size)
                profile = DatastreamProfile(object_id, ds_id)
                profile.fetch()
                fmd = FileItemMetadata(object_id)
                fmd.fetch()
                server_date = utils.as_w3c_datetime(meta["Date"])
                filename = meta["filename"]
                local_path = meta["local-path"]
                media_type = meta["Content-Type"]
                size = int(meta["Content-Length"])

                sha1 = utils.sha1_for_file(local_path)
                if sha1 != profile.ds_checksum:
                    checksum_error = sha1
                    checksum_error_count += 1
                else:
                    checksum_error = ""

                csv_writer.writerow([object_id, ds_id, server_date, filename, fmd.fmd_path, local_path,
                                     media_type, size,
                                     profile.ds_checksum_type, profile.ds_checksum, profile.ds_creation_date,
                                     fmd.fmd_creator_role, fmd.fmd_visible_to, fmd.fmd_accessible_to,
                                     checksum_error])
        return checksum_error_count

    def verify_checksums(self, log_file, has_header=True, col_local_path=5, col_checksum=9):
        """
        Verify sha1 checksums over a bunch of files listed in `log_file`. This method creates a new `log_file{x}`,
        alongside the old one, where `x` is an ordinal number. The new `log_file{x}` will be a copy of the
        `log_file` with an additional column in which checksum errors will be reported.

        :param log_file: name of the file containing local_path and previously calculated sha1 in columns
        :param has_header: does the `log_file` have column headings, default: True
        :param col_local_path: the column number (zero-based) that contains the local path to each inspected file
        :param col_checksum: the column number (zero-based) that contains the previously computed sha1
        :return: count of checksum errors
        """
        abs_log_file = os.path.abspath(log_file)
        parts = os.path.splitext(os.path.basename(abs_log_file))
        digits = re.findall("\d+", parts[0])
        ordinal = (int(digits[0]) if len(digits) > 0 else 0) + 1
        base_name = ''.join(i for i in parts[0] if not i.isdigit())
        new_log_file = os.path.join(os.path.dirname(abs_log_file), base_name + str(ordinal) + parts[1])

        checksum_error_count = 0
        with open(abs_log_file, "r", newline='') as old_log, open(new_log_file, "w", newline='') as new_log:
            reader = csv.reader(old_log, dialect=self.dialect)
            writer = csv.writer(new_log, dialect=self.dialect)
            if has_header:
                headers = next(reader, None)
                if headers:
                    headers.append("checksum_error_" + str(ordinal))
                    writer.writerow(headers)
            for row in reader:
                LOG.debug("Verify sha1 checksum: %s" % row[col_local_path])
                sha1 = utils.sha1_for_file(row[col_local_path])
                if sha1 != row[col_checksum]:
                    checksum_error = sha1
                    checksum_error_count += 1
                    LOG.warning("Found compromised sha1: %s" % row[col_local_path])
                else:
                    checksum_error = ""
                row.append(checksum_error)
                writer.writerow(row)
        return checksum_error_count

    @staticmethod
    def id_iter(id_list):
        if isinstance(id_list, str):
            with open(id_list, "r") as id_file:
                for line in id_file:
                    yield line.rstrip()
        elif isinstance(id_list, list):
            for id in id_list:
                yield id