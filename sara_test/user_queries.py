#!/usr/bin/env python

import argparse
import datetime
import glob
import os
import random
from multiprocessing.pool import ThreadPool as Pool
from threading import current_thread as current_process
import subprocess
import requests
from distutils import spawn


# CONSTANTS
SARA_SVR='https://copernicus-dev.nci.org.au/'
#SARA_SEARCH_URL='https://copernicus-dev.nci.org.au/sara.server/1.0/api/collections/'
SARA_SEARCH_URL=''
SEARCH_URL='sara.server/1.0/api/collections/'
SARA_SEARCH_CMD='./auscophub_searchSara.py'


def main():
    p = argparse.ArgumentParser(description="Run user query test.")
    p.add_argument("--nq", type=int, default=5, help="Number of concurrent queries (default=%(default)s)")
    p.add_argument("--outputdir", default="query_result", help="Directory for output (default=%(default)s)")
    p.add_argument("--searchSara", default=False, action="store_true", help="Use auscophub_searchSARA for test (default=%(default)s)")
    #p.add_argument("--download", default=False, action="store_true", help="Test download after queries.")
    p.add_argument("--server", default=SARA_SVR, help="Server to query (default=%(default)s)")
    
    cmdargs= p.parse_args()

    global SARA_SEARCH_URL
    SARA_SEARCH_URL = '{}/{}'.format(cmdargs.server, SEARCH_URL)

    #if cmdargs.searchSara and spawn.find_executable(SARA_SEARCH_CMD):
    if cmdargs.searchSara:
        search_function = run_search
    else:
        search_function = run_requests

    #make output directory
    if not os.path.exists(cmdargs.outputdir):
        os.mkdir(cmdargs.outputdir)
    os.chdir(cmdargs.outputdir)
        
    # get current time
    now=datetime.datetime.utcnow()

    #define product availability windows
    product_windows={'RAW': [datetime.datetime(2014, 10, 1, 0, 0), now], 
                     'GRD': [datetime.datetime(2014, 10, 1, 0, 0), now], 
                     'SLC': [datetime.datetime(2014, 10, 1, 0, 0), now],
                     'L1C': [datetime.datetime(2015, 7, 1, 0, 0), now],
                     'OL_1_ERR___': [datetime.datetime(2016, 10, 1, 0, 0),now],
                     'OL_1_EFR___': [datetime.datetime(2016, 10, 1, 0, 0), now],
                     'OL_2_LFR___': [datetime.datetime(2017, 6, 1, 0, 0), now],
                     'OL_2_LRR___': [datetime.datetime(2017, 7, 1, 0, 0), now],
                     'OL_2_WFR___': [datetime.datetime(2017, 7, 1, 0, 0), now],
                     'OL_2_WRR___': [datetime.datetime(2017, 7, 1, 0, 0), now],
                     'SL_2_WST___': [datetime.datetime(2017, 7, 1, 0, 0), now],
                     'SL_2_LST___': [datetime.datetime(2017, 7, 1, 0, 0), now],
                     'SL_1_RBT___': [datetime.datetime(2016, 11, 1, 0, 0), now],
                     'SR_1_SRA___': [datetime.datetime(2016, 6, 1, 0, 0), now],
                     'SR_1_SRA_A_': [datetime.datetime(2016, 6, 1, 0, 0), now],
                     'SR_1_SRA_BS': [datetime.datetime(2016, 6, 1, 0, 0), now],
                     'SR_2_LAN___': [datetime.datetime(2016, 10, 1, 0, 0), now],
                     'SR_2_WAT___': [datetime.datetime(2016, 12, 1, 0, 0), now],
                     }
    producttypes=product_windows.keys()

    if not product_windows:    
    #find producttypes and time windows
        producttypes=[pt.split('/')[-1] for pt in glob.glob('/g/data/fj7/Copernicus/Sentinel-1/*/*')]
        producttypes+=[pt.split('/')[-1] for pt in glob.glob('/g/data/fj7/Copernicus/Sentinel-2/*/*')]
        producttypes+=[pt.split('/')[-1] for pt in glob.glob('/g/data/fj7/Copernicus/Sentinel-3/*/*')]
        producttypes = [pt for pt in producttypes if pt !='OCN']
        
        product_windows={}
        for pt in producttypes:
            yearmonths=[datetime.datetime.strptime(ym.split('/')[-1],'%Y-%m') for ym in glob.glob('/g/data/fj7/Copernicus/Sentinel-?/*/%s/*/*'%pt)]
            yearmonths.sort()
            product_windows[pt]=[yearmonths[0],now]


    # fix SEED
    random.seed(a=0)

    #random product types
    nproducttypes=len(producttypes)
    pt_ind = [random.randint(0,nproducttypes-1) for i in range(cmdargs.nq)]
    producttypes=[producttypes[ind] for ind in pt_ind]
    
    #random start date and end date
    window_start=[]
    window_end=[]
    for pt in producttypes:
        window=(product_windows[pt][1]-product_windows[pt][0]).days
        offsets = [random.randint(0, window) for i in range(2)]
        window_start.append((product_windows[pt][0]+datetime.timedelta(days=min(offsets))).strftime('%Y-%m-%d'))
        window_end.append((product_windows[pt][0]+datetime.timedelta(days=max(offsets))).strftime('%Y-%m-%d'))

    #random polygons
    #eastern hemsphere
    nq_e=int(cmdargs.nq*0.9)
    #western
    nq_w=cmdargs.nq-nq_e
    #random lat lons
    lat_range=[-90., 28.]
    lon_range_e=[40., 180.]
    lon_range_w=[-180.,-150.]
    
    latwindows = [[random.uniform(lat_range[0],lat_range[1]) for i in range(2)] for j in range(cmdargs.nq)]
    lat_min=[min(wd) for wd in latwindows]
    lat_max=[max(wd) for wd in latwindows]

    lonwindows_e = [[random.uniform(lon_range_e[0], lon_range_e[1]) for i in range(2)] for j in range(nq_e)]
    lonwindows_w = [[random.uniform(lon_range_w[0], lon_range_w[1]) for i in range(2)] for j in range(nq_w)]
    lon_min=[min(wd) for wd in lonwindows_e]+[min(wd) for wd in lonwindows_w]
    lon_max=[max(wd) for wd in lonwindows_e]+[max(wd) for wd in lonwindows_w]

    polygons=['POLYGON((%.2f %.2f, %.2f %.2f, %.2f %.2f, %.2f %.2f, %.2f %.2f))'%(
            lon_min[i], lat_min[i], lon_max[i], lat_min[i], lon_max[i], lat_max[i],
            lon_min[i], lat_max[i], lon_min[i], lat_min[i]) for i in range(len(lat_min))]

    
    #construct random queries
    queries=["productType=%s&startDate=%s&completionDate=%s&geometry=%s"%(
            producttypes[i],window_start[i],window_end[i],polygons[i]
            ) for i in range(len(producttypes))]
    

    #start a pool of workers
    qpool=Pool(cmdargs.nq)
    
    with open('summary','w') as res:
        for output,time_used in qpool.imap(search_function, queries):
            output_list=open(output).readlines()
            threadNum = output.split('_')[1]
            print >>res, "%s: %s seconds used to find %s products"%(threadNum,time_used,len(output_list)-1)
        
    qpool.close()
    qpool.join()
    

def run_requests(query):
    """
    use requests to query
    """
    #output file named with worker number
    worker= current_process()
    output= "urllist_%s"%worker.name
    
    #start query page 0
    start=datetime.datetime.now()
    qurl="%s/search.json?%s&index=1&maxRecords=50"%(SARA_SEARCH_URL, query)

    r= requests.get(qurl)
    rjson=r.json()
    nresults=rjson["properties"]["itemsPerPage"]
    producturls=[f["properties"]["links"][0]["href"] for f in rjson["features"]]
    
    while nresults>0:
        qurl_page="%s&index=%d"%(qurl,len(producturls)+1)
        r= requests.get(qurl_page)
        rjson=r.json()
        nresults=rjson["properties"]["itemsPerPage"]
        producturls+=[f["properties"]["links"][0]["href"] for f in rjson["features"]]

    time_used=datetime.datetime.now()-start
    
    with open(output,'w') as op:
        print >>op, qurl
        for purl in producturls: print >>op, purl
    
    return output, time_used.days*24*3600.+time_used.seconds
    

def run_search(query):
    """
    call auscophub_searchSara.py
    """
    
    #output file named with worker number
    worker= current_process()
    output= "curlscript_%s"%worker.name

    #construct call
    cmd = SARA_SEARCH_CMD
    for q in query.split('&'):
        cmd+=" --queryparam \"%s\""%q
    cmd+= " --curlscript %s"%(output)

    print 'XXX', cmd

    start=datetime.datetime.now()
    proc=subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stderr, stdout=proc.communicate()
    if stderr or stdout: print stderr, stdout

    time_used=datetime.datetime.now()-start
    
    return output, time_used.days*24*3600.+time_used.seconds

    
if __name__=="__main__":
    main()

