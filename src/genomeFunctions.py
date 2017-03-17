#!/usr/bin/env python

import os
import logging.config
import re
import Bio.SeqIO
import tempfile
import subprocess

log = logging.getLogger(__name__)


def get_files_as_list(file_or_directory):
    """
    Creates a list of files from either the given file, or all files within the
    directory specified (where each file name is its absolute path).

    :param file_or_directory: file or directory name given on commandline
    :return files_list: List of all the files found.

    """

    files_list = []

    if os.path.isdir(file_or_directory):
        log.info("Gathering genomes from directory " + file_or_directory)

        # Create a list containing the file names
        for root, dirs, files in os.walk(file_or_directory):
            for filename in files:
                files_list.append(os.path.join(root, filename))

    else:
        log.info("Using genomes in file " + file_or_directory)
        files_list.append(os.path.abspath(file_or_directory))

    # check that all are valid fasta files
    # if not, exclude with warning
    validated_files_list = validate_fasta_files(files_list)

    return sorted(validated_files_list)


def validate_fasta_files(files):
    """
    Check using Bio.SeqIO if files are valid fasta format.

    :param files: full path of all files
    :return: a list of all files that pass
    """

    validated_files = []
    for file in files:
        for _ in Bio.SeqIO.parse(file, "fasta"):
            log.debug("%s is a valid fasta file", file)
            validated_files.append(file)

            break

    return validated_files


def get_genome_name(filename):
    """
    Getting the name of the genome by hierarchy. This requires reading the first
    fasta header from the file. It also assumes a single genome per file.

    :param filename: Name of the file containing the record.
    :return genomeName: Name of the genome contained in the file (or sequence).
    """

    record_id = get_fasta_header_from_file(filename)

    # Look for lcl followed by the possible genome name
    if re.search('lcl\|([\w-]*)', record_id):
        match = re.search('lcl\|([\w-]*)', record_id)
        match = str(match.group())
        genome_name = match.split('|')[1]

    # Look for a possible genome name at the beginning of the record ID
    elif re.search('(^[a-zA-Z][a-zA-Z]\w{6}\.\d)', record_id):
        match = re.search('(\w{8}\.\d)', record_id)
        genome_name = str(match.group())

    # Look for ref, gb, emb or dbj followed by the possible genome name
    elif re.search('(ref\|\w{2}_\w{6}|gb\|\w{8}|emb\|\w{8}|dbj\|\w{8})',
                   record_id):
        match = re.search('(ref\|\w{2}_\w{6}|gb\|\w{8}|emb\|\w{8}|dbj\|\w{8})',
                          record_id)
        match = str(match.group())
        genome_name = match.split('|')[1]

    # Look for gi followed by the possible genome name
    elif re.search('gi\|\d{8}', record_id):
        match = re.search('gi\|\d{8}', record_id)
        match = str(match.group())
        genome_name = match.split('|')[1]

    # Assign the file name as genome name
    else:
        genome_name = filename

    return genome_name


def get_fasta_header_from_file(filename):
    """
    Gets the first fasta sequence from the file, and returns the fasta header.
    The files should have already been validated as fasta format.

    :param filename: the absolute path of the fasta file
    :return: header
    """

    for record in Bio.SeqIO.parse(filename, "fasta"):
        return record.description


def create_blast_db(filelist):
    """
    Creating a blast DB using the makeblastdb command.
    The database is created in the temporary folder of the system.

    :param filelist: genome list that was given by the user on the commandline.
    :return full path of DB, or FALSE if makeblastdb failed
    """

    tempdir = tempfile.mkdtemp()
    blast_db_path = os.path.join(tempdir, 'ectyper_blastdb')

    # combine all file names into a single string for use with makeblastdb
    files_string = ' '.join(filelist)
    log.debug("Combined list of files for makeblastdb: %s", files_string)

    log.debug("Generating the blast db at %s", blast_db_path)
    completed_process = subprocess.run(["makeblastdb",
                                        "-in", files_string,
                                        "-dbtype", "nucl",
                                        "-title", "ectyper_blastdb",
                                        "-out", blast_db_path],
                                       check=True)

    if completed_process.returncode == 0:
        return blast_db_path
    else:
        return False
