"""
 .. module:: upload.utils

    :synopsis: Helper functions for uploads
"""

import os
import magic
import subprocess

import app.lib.file_utils as fu

from flask import current_app
from app import (
    celery,
    upload_redis as redis
)
from app.constants import UPDATED_FILE_DIRNAME
from app.upload.constants import (
    ALLOWED_MIMETYPES,
    MAX_CHUNKSIZE,
    upload_status,
)
from app.models import Files


def parse_content_range(header):
    """
    Extracts the starting byte position and resource length.

    Content-Range = "Content-Range" ":" content-range-spec

    content-range-spec      = byte-content-range-spec
    byte-content-range-spec = bytes-unit SP
                              byte-range-resp-spec "/"
                              ( instance-length | "*" )
    byte-range-resp-spec    = (first-byte-pos "-" last-byte-pos)
                                  | "*"
    instance-length         = 1*DIGIT

    :param header: the rhs of the content-range header
    :return: the first-byte-pos and instance-length
    """
    bytes_ = header.split(' ')[1]
    return int(bytes_.split('-')[0]), int(bytes_.split('/')[1])


def upload_exists(request_id, filename):
    """
    Checks for an existing uploaded file.

    :param request_id: id of request associated with the upload
    :param filename: the name of the uploaded file
    :return: whether the file exists or not
    """
    existing_filenames = [
        file_.name for file_ in
        Files.query.filter_by(
            request_id=request_id,
            deleted=False,
        ).all()
    ]
    return filename in existing_filenames


def is_valid_file_type(obj):
    """
    Validates the mime type of a file.
    Content type header is ignored.

    :param obj: the file storage object to check
    :type obj: werkzeug.datastructures.FileStorage

    :return: (whether the mime type is allowed or not,
        the mime type)
    """
    buffer = obj.stream.read(MAX_CHUNKSIZE)
    # 1. Check using default
    mime_type = magic.from_buffer(buffer, mime=True)
    is_valid = mime_type in ALLOWED_MIMETYPES
    if is_valid and current_app.config['MAGIC_FILE'] != '':
        # 3. Check using custom
        m = magic.Magic(
            magic_file=current_app.config['MAGIC_FILE'],
            mime=True)
        m.from_buffer(buffer)
        is_valid = mime_type in ALLOWED_MIMETYPES
    obj.stream.seek(0)
    return is_valid, mime_type


def get_upload_key(request_id, upload_filename, for_update=False):
    """
    Returns a formatted key for an upload.
    Intended for tracking the status of an upload.

    :param request_id: id of the request associated with the upload
    :param upload_filename: the name of the uploaded file
    :param for_update: will the uploaded file replace an existing file?
        (this is required to make keys unique, as the uploaded file
        may share the same name as the existing file)

    :return: the formatted key
        Ex.
            FOIL-ID_filename.ext_new
            FOIL_ID_filename.ext_update
    """
    return '_'.join((request_id,
                     upload_filename,
                     'update' if for_update else 'new'))


class VirusDetectedException(Exception):
    """
    Raise when scanner detects an infected file.
    """
    def __init__(self, filename):
        super(VirusDetectedException, self).__init__(
            "Infected file '{}' removed.".format(filename))


@celery.task
def scan_and_complete_upload(request_id, filepath, is_update=False):
    """
    Scans an uploaded file (see scan_file) and moves
    it to the data directory if it is clean. If is_update is set,
    the file will also be placed under the 'updated' directory.
    Updates redis accordingly.

    :param request_id: id of request associated with the upload
    :param filepath: path to uploaded and quarantined file
    :param is_update: will the file replace an existing one?
    """
    filename = os.path.basename(filepath)

    key = get_upload_key(request_id, filename, is_update)
    redis.set(key, upload_status.SCANNING)

    try:
        scan_file(filepath)
    except VirusDetectedException:
        redis.delete(key)
    else:
        # complete upload
        dst_dir = os.path.join(
            current_app.config['UPLOAD_DIRECTORY'],
            request_id
        )
        if is_update:
            dst_dir = os.path.join(
                dst_dir,
                UPDATED_FILE_DIRNAME
            )
        if not fu.exists(dst_dir):
            try:
                fu.makedirs(dst_dir)
            except OSError as e:
                # in the time between the call to fu.exists
                # and fu.makedirs, the directory was created
                print(e.args)

        fu.move_to_sftp_server(
            filepath,
            os.path.join(dst_dir, filename)
        )
        redis.set(key, upload_status.READY)


def scan_file(filepath):
    """
    Scans a file for viruses using McAfee Virus Scan. If an infected
    file is detected, removes the file and raises VirusDetectedException.

    :param filepath: path of file to scan
    """
    if current_app.config['VIRUS_SCAN_ENABLED']:
        options = [
            '--analyze',  # Use heuristic analysis to find possible new viruses
            '--atime-preserve',  # Preserve the file's last-accessed time and date
            '--delete'  # Automatically delete the infected file
        ]
        cmd = ['uvscan'] + options + [filepath]
        subprocess.call(cmd)  # TODO: redirect output to logfile
        # if the file was removed, it was infected
        if not os.path.exists(filepath):
            raise VirusDetectedException(os.path.basename(filepath))
