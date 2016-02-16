"""
api/models.py
"""
from django.db import models
from django.conf import settings

import os
import logging
import plistlib
from xml.parsers.expat import ExpatError

from munkiwebadmin.utils import MunkiGit

REPO_DIR = settings.MUNKI_REPO_DIR

LOGGER = logging.getLogger('munkiwebadmin')

try:
    GIT = settings.GIT_PATH
except AttributeError:
    GIT = None

class PlistError(Exception):
    '''Class for Plist errors'''
    pass


class PlistReadError(PlistError):
    '''Error reading a plist'''
    pass


class PlistWriteError(PlistError):
    '''Error writing a plist'''
    pass


class PlistDeleteError(PlistError):
    '''Error deleting a plist'''
    pass


class PlistDoesNotExistError(PlistError):
    '''Error when plist doesn't exist at pathname'''
    pass


class PlistAlreadyExistsError(PlistError):
    '''Error when creating a new plist at an existing pathname'''
    pass


class Plist(object):
    '''Pseudo-Django object'''
    @classmethod
    def list(cls, kind):
        '''Returns a list of available plists'''
        kind_dir = os.path.join(REPO_DIR, kind)
        plists = []
        skipdirs = ['.svn', '.git', '.AppleDouble']
        for dirpath, dirnames, filenames in os.walk(kind_dir):
            for skipdir in skipdirs:
                if skipdir in dirnames:
                    dirnames.remove(skipdir)
            subdir = dirpath[len(kind_dir):]
            plists.extend([os.path.join(subdir, name).lstrip('/')
                          for name in filenames if not name.startswith('.')])
        return plists

    @classmethod
    def new(cls, kind, pathname, user, plist_data=None):
        '''Returns a new plist object'''
        kind_dir = os.path.join(REPO_DIR, kind)
        filepath = os.path.join(kind_dir, pathname)
        if os.path.exists(filepath):
            raise PlistAlreadyExistsError(
                '%s/%s already exists!' % (kind, pathname))
        plist_parent_dir = os.path.dirname(filepath)
        if not os.path.exists(plist_parent_dir):
            try:
                # attempt to create missing intermediate dirs
                os.makedirs(plist_parent_dir)
            except (IOError, OSError), err:
                LOGGER.error('Create failed for %s/%s: %s', kind, pathname, err)
                raise PlistWriteError(err)
        if plist_data:
            plist = plist_data
        else:
            # create a useful empty plist
            if kind == 'manifests':
                plist = {}
                for section in [
                        'catalogs', 'included_manifests', 'managed_installs',
                        'managed_uninstalls', 'managed_updates',
                        'optional_installs']:
                    plist[section] = []
            elif kind == "pkgsinfo":
                plist = {
                    'name': 'ProductName',
                    'display_name': 'Display Name',
                    'description': 'Product description',
                    'version': '1.0',
                    'catalogs': ['development']
                }
        data = plistlib.writePlistToString(plist)
        try:
            with open(filepath, 'w') as fileref:
                fileref.write(data.encode('utf-8'))
            LOGGER.info('Created %s/%s', kind, pathname)
            if user and GIT:
                MunkiGit().add_file_at_path(filepath, user)
        except (IOError, OSError), err:
            LOGGER.error('Create failed for %s/%s: %s', kind, pathname, err)
            raise PlistWriteError(err)
        return data

    @classmethod
    def read(cls, kind, pathname):
        '''Reads a plist file and returns the plist as a dictionary'''
        kind_dir = os.path.join(REPO_DIR, kind)
        filepath = os.path.join(kind_dir, pathname)
        if not os.path.exists(filepath):
            raise PlistDoesNotExistError()
        try:
            plistdata = plistlib.readPlist(filepath)
            return plistdata
        except (IOError, OSError), err:
            LOGGER.error('Read failed for %s/%s: %s', kind, pathname, err)
            raise PlistReadError(err)
        except (ExpatError, IOError):
            # could not parse, return empty dict
            return {}

    @classmethod
    def write(cls, data, kind, pathname, user):
        '''Writes a plist file'''
        kind_dir = os.path.join(REPO_DIR, kind)
        filepath = os.path.join(kind_dir, pathname)
        plist_parent_dir = os.path.dirname(filepath)
        if not os.path.exists(plist_parent_dir):
            try:
                # attempt to create missing intermediate dirs
                os.makedirs(plist_parent_dir)
            except OSError, err:
                LOGGER.error('Create failed for %s/%s: %s', kind, pathname, err)
                raise PlistWriteError(err)
        try:
            with open(filepath, 'w') as fileref:
                fileref.write(data)
            LOGGER.info('Wrote %s/%s', kind, pathname)
            if user and GIT:
                MunkiGit().add_file_at_path(filepath, user)
        except (IOError, OSError), err:
            LOGGER.error('Write failed for %s/%s: %s', kind, pathname, err)
            raise PlistWriteError(err)

    @classmethod
    def delete(cls, kind, pathname, user):
        '''Deletes a plist file'''
        kind_dir = os.path.join(REPO_DIR, kind)
        filepath = os.path.join(kind_dir, pathname)
        if not os.path.exists(filepath):
            raise PlistDoesNotExistError(
                '%s/%s does not exist' % (kind, pathname))
        try:
            os.unlink(filepath)
            LOGGER.info('Deleted %s/%s', kind, pathname)
            if user and GIT:
                MunkiGit().delete_file_at_path(filepath, user)
        except (IOError, OSError), err:
            LOGGER.error('Delete failed for %s/%s: %s', kind, pathname, err)
            raise PlistDeleteError(err)
