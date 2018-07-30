#!/usr/bin/env python

from os.path import getsize
import hashlib
from urllib.parse import ParseResult, urljoin
from pathlib import Path
import uuid
import json
import requests
from dateutil import parser
import click
from shapely.geometry import Polygon, mapping


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


def bounding_box(json_fname):
    """
    Given an a JSON file from the CSIRO MERIS data collection
    return a JSON mapping of a shapely geometry.

    For this ingest example return WGS84 lon/lat coords.
    """
    with open(json_fname, 'r') as src:
        lonlat = json.load(src)

    poly = Polygon(list(zip(lonlat['lon'], lonlat['lat'])))
    return mapping(poly)


def parse_cdl(cdl_fname):
    """
    A simple util to parse *SOME* items from the common data language file.

    *************************************************************************
    Do not rely on this func, it is just to get by for a prototype ingestion.
    *************************************************************************

    Ed King might have something available that grabs everything.
    GDAL might (after gunzip is applied), or netcdf tools.
    """
    with open(cdl_fname, 'r') as src:
        cdl = [line.strip() for line in src.readlines()]

    # there is a lot more metadata that could be used, but we'll just grab some key items
    global_list = cdl[cdl.index('// global attributes:') + 1:-1]

    # remove starting ':' and ending ';', and strip surrounding white space, and replace " with empty
    global_md = {k.strip(): v.strip().replace('"', '') for (k, v) in [i[1:-1].split('=') for i in global_list]}

    # gather other useful info
    idx = cdl.index('byte metadata ;')

    # remove starting 'metadata:MPH\\:' and ending ';', and replace " with empty
    other = [i[i.index('\\')+2:-1] for i in cdl[idx+1:idx+14]]
    other_md = {k.strip(): v.strip().replace('"', '') for (k, v) in [i.split('=') for i in other]}

    return other_md, global_md


def ingest(basedir, username, password, protocol='http',
           server_url='localhost', endpoint='aodh/', verbose=True):
    """
    Find the meris data published by CSIRO and create resto compliant
    JSON metadata.
    This example will ingest the MERIS FDG 1P data, using the collection
    name MERFSG1P.

    We'll ingest using the web path rather than the file path on NCI

    http://remote-sensing.nci.org.au/u39/public/data/meris/

    ***** These params should be passed from the command line *****
    protocol -> http
    server-url -> remote-sensing.nci.org.au
    endpoint -> /u39/public/data/meris/

    Will run this script twice:
        * 1 -> generate json files on NCI
        * 2 -> copy json files to my pc then ingest to my local instance of resto
               the test database will use the params:
               http
               localhost
               resto/
    """
    # importing posixpath.join as urljoin should get around the annoying way
    # urlparse.urljoin handles ending '/' and preceeding '/'
    # eg
    # urlparse.urljoin('/media/path', 'js/foo.js') -> '/js/foo.js'
    # urlparse.urljoin('/media/path', '/js/foo/js') -> '/media/js/foo.js'
    # urlparse.urljoin('/media/path/', 'js/foo/js') -> '/media/path/js/foo.js'

    # piece together the url path
    url = ParseResult(scheme=protocol, netloc=server_url, path=endpoint,
                      params='', query='', fragment='')
    urlpath = urljoin(urljoin(url.geturl(), 'collections/'), 'MERFSG1P')

    base_path = Path(basedir)

    # ingest the found HDF5 files
    for cdl_fname in base_path.rglob('*.cdl'):
        # return some base info from the cdl file
        other_md, global_md = parse_cdl(str(cdl_fname))

        # separate the basepath from the rest of the directory tree
        lower_tree = str(cdl_fname.parent).replace(str(basedir), '')[1:]
        base_url = '{}/'.format(urljoin(url.geturl(), lower_tree))

        # resto has to labels for quicklook -> quicklook and thumbnail
        # i'm unsure if they're meant to be the same thing giving people a label choice,
        # or whether thumbnail is for the display on the client gui and quicklook for something else
        # anyway, for this example we'll use thumbnail for the jpeg and quicklook for the full res png
        json_fname = base_path.joinpath(lower_tree, '{}.json'.format(cdl_fname.stem))
        th_fname = base_path.joinpath(lower_tree, '{}.1024.jpg'.format(cdl_fname.stem))
        ql_fname = base_path.joinpath(lower_tree, '{}.png'.format(cdl_fname.stem))
        nc_fname = base_path.joinpath(lower_tree, '{}.nc.gz'.format(cdl_fname.stem))

        # thumbnail, quicklook and nc file we'll use the public url
        th_url = urljoin(base_url, str(th_fname.name))
        ql_url = urljoin(base_url, str(ql_fname.name))
        nc_url = urljoin(base_url, str(nc_fname.name))


        # resto properties
        properties = {
            'resource': nc_url,
            'resourceSize': getsize(str(nc_fname)),
            'resourceChecksum': 'md5={}'.format(md5(str(nc_fname))),
            'productIdentifier': nc_fname.name,
            'quicklook': ql_url,
            'thumbnail': th_url,
            'startDate': parser.parse(global_md['start_date']).isoformat(),
            'completionDate': parser.parse(global_md['stop_date']).isoformat(),
            'productType': global_md['product_type'],
            'description': global_md['title'],
            'orbitNumber': int(other_md['ABS_ORBIT']),
            'organisationName': 'CSIRO',
            'platform': 'Envisat',
            'instrument': 'MERIS'
        }

        data = {
            'type': 'Feature',
            'id': str(uuid.uuid4()),
            'geometry': bounding_box(str(json_fname)),
            'properties': properties
        }

        # testing purposes only; output json file
        # these need to be downloaded and ingested onto my local instance
        outdir = Path("/g/data/v10/testing_ground/jps547/cophub-aodh/meris")
        out_fname = outdir.joinpath("{}.json".format(cdl_fname.stem))
        with open(out_fname, 'w') as src:
            json.dump(data, src, indent=4)

        # post
        # response = requests.post(urlpath, data=json.dumps(data, indent=4),
        #                          auth=(username, password))

        # if verbose:
        #     print(cdl_fname, response.text)


@click.command()
@click.option("--basedir", type=click.Path(exists=True, readable=True),
              help="The base directory to search for MERIS '*.cdl' files.")
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
