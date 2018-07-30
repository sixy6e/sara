#!/usr/bin/env python

from os.path import getsize
import hashlib
from urllib.parse import ParseResult, urljoin
from functools import partial
from pathlib import Path
import uuid
import requests
import yaml
import json
import click
import h5py
from shapely.geometry import Polygon, mapping
from wagl.geobox import GriddedGeoBox
from wagl.hdf5 import find


def md5(fname):
    """
    Adopted from:
    https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
    """
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as src:
        # process in ~100MB chunks
        for chunk in iter(lambda: src.read(104857600), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def find_pattern(pattern, name):
    """
    A simple util to find the first hit matching a pattern.
    """
    if pattern in name:
        return name


def bounding_box(dataset):
    """
    Given an HDF5 IMAGE CLASS Dataset, return a json mapping
    of a shapely geometry.

    For this ingest example return WGS84 lon/lat coords.
    """
    geobox = GriddedGeoBox.from_dataset(dataset)
    poly = Polygon([geobox.ul_lonlat,
                    geobox.ur_lonlat,
                    geobox.lr_lonlat,
                    geobox.ll_lonlat])
    return mapping(poly)


def ingest(basedir, username, password, protocol='http',
           server_url='localhost', endpoint='aodh/', verbose=True):
    """
    Find wagl generated HDF5 files and ingest into resto.
    """
    # piece together the url path
    url = ParseResult(scheme=protocol, netloc=server_url, path=endpoint,
                      params='', query='', fragment='')
    urlpath = urljoin(urljoin(url.geturl(), 'collections/'), 'GAARD')

    base_path = Path(basedir)

    # ingest the found HDF5 files
    for h5_file in base_path.rglob('*.h5'):
        with h5py.File(str(h5_file), 'r') as fid:

            # find the first STANDARDISED-PRODUCT
            img_paths = find(fid, 'IMAGE')
            img_pth = [p for p in img_paths if 'STANDARDISED-PRODUCTS' in p][0]

            # TODO generate quicklook

            # dataset metadata
            ds = fid[fid.visit(partial(find_pattern, 'NBAR-METADATA'))]
            md = yaml.load(ds[()])

            # resto properties
            # 'quicklook': '' # TODO
            properties = {
                'resource': str(h5_file.absolute()),
                'resourceSize': getsize(str(h5_file)),
                'resourceChecksum': 'md5={}'.format(md5(str(h5_file))),
                'productIdentifier': h5_file.name,
                'startDate': md['source_datasets']['acquisition_datetime'],
                'platform': md['source_datasets']['platform_id'],
                'instrument': md['source_datasets']['sensor_id']
            }

            data = {
                'type': 'Feature',
                'id': str(uuid.uuid4()),
                'geometry': bounding_box(fid[img_pth]),
                'properties': properties
            }

            # testing purposes only; output json file
            out_fname = base_path.joinpath("{}.json".format(h5_file.stem))
            with open(out_fname, 'w') as src:
                json.dump(data, src, indent=4)

            # post
            response = requests.post(urlpath, data=json.dumps(data, indent=4),
                                     auth=(username, password))

            if verbose:
                print(h5_file, response.text)


@click.command()
@click.option("--basedir", type=click.Path(exists=True, readable=True),
              help="The base directory to search for wagl HDF5 files.")
@click.option("--username", required=True, help="Database user name.")
@click.option("--password", required=True, help="Database password.")
@click.option("--protocol", default="http", help="Server protocol.")
@click.option("--server-url", default="localhost", help="Server url.")
@click.option("--endpoint", default="resto/", help="Server endpoint.")
@click.option("--verbose", default=False, is_flag=True, help="Print response.")
def main(basedir, username, password, protocol='http', server_url='localhost',
         endpoint='aodh', verbose=True):
    """
    Main level program.
    """
    ingest(basedir, username, password, protocol, server_url, endpoint,
           verbose)


if __name__ == '__main__':
    main()
