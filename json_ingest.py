#!/usr/bin/env python

from urllib.parse import ParseResult, urljoin
import json
import tarfile
import requests
import click


def ingest(tarball, username, password, collection, protocol='http',
           server_url='localhost', endpoint='aodh/', verbose=True):
    """
    Find the meris data published by CSIRO and ingest into resto.

    We'll ingest using the web path

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
    urlpath = urljoin(urljoin(url.geturl(), 'collections/'), collection)

    # for this script just re-use the basedir variable for the tarfile
    with tarfile.open(tarball, 'r') as tf:
        member = tf.next()
        while member:
            if member.isfile():
                # read data as dict object, as the raw string read using tar gives bytes not unicode
                data = json.load(tf.extractfile(member))

                # post
                response = requests.post(urlpath,
                                         data=json.dumps(data, indent=4),
                                         auth=(username, password))

                if verbose:
                    print(member.name, response.text)

            member = tf.next()


@click.command()
@click.option("--tarball", type=click.Path(exists=True, readable=True),
              help="The tarball containing the json files generated from 09a_ingest_meris.py")
@click.option("--username", required=True, help="Database user name.")
@click.option("--password", required=True, help="Database password.")
@click.option("--protocol", default="http", help="Server protocol.")
@click.option("--server-url", default="localhost", help="Server url.")
@click.option("--endpoint", default="resto/", help="Server endpoint.")
@click.option("--collection", help="Server endpoint.", required=True)
@click.option("--verbose", default=False, is_flag=True, help="Print response.")
def main(basedir, username, password, collection, protocol='http',
         server_url='localhost', endpoint='aodh', verbose=True):
    """
    Main level program.
    """
    ingest(basedir, username, password, collection, protocol, server_url,
           endpoint, verbose)


if __name__ == '__main__':
    main()
