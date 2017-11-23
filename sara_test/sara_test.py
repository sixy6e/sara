#!/usr/bin/env python
"""
Wrapper script to run the SARA query tests
  (requires module: requests)
""" 

### IMPORTS ###
import subprocess as sp


### GLOBALS ###
saraSvr = 'https://copernicus-dev.nci.org.au/'
nThreads = 10
outDir = './query_result'

### FUNCTIONS ###
def check_requests():
    try:
        import requests
    except importError:
        print 'Need to install requests module ...'
        # check if pip installed
        cmd = 'which pip'
        if sp.call(cmd, shell=True):
            print 'pip not found - try installing via yum ...'
            cmd = 'sudo yum install python-requests'
            if sp.call(cmd, shell=True):
                print 'Error while executing: {}'.format(cmd)
                exit(1)
        else:
            cmd = 'pip install requests'
            if sp.call(cmd, shell=True):
                print 'Error while executing: {}'.format(cmd)
                exit(1)

### MAIN ###
def main():
    # check if python requests module installed
    check_requests()

    print '\n--- SARA Query Test (could take a few mins) ---'
    
# now can run the query
    cmd = 'python user_queries.py --server {} --nq {} --outputdir {}'.format(saraSvr, nThreads, outDir)
    if sp.call(cmd, shell=True):
        print 'Error while executing: {}'.format(cmd)
        exit(1)

    # check results
    res = []
    summ = []
    for i in range(nThreads):
        cmd = 'head -1 {}/urllist_Thread-{}'.format(outDir, i + 1)
        res.append(sp.check_output(cmd, shell=True))
        summ.append(i)

    with open('{}/summary'.format(outDir)) as fin:
         tempS = list(fin)

    # need to reorder results because 'summary' file is in random thread order
    for i in range(nThreads):
        idx = int(tempS[i].split(':')[0].split('-')[1]) - 1
        val = tempS[i].split(':')[1]
        summ[idx] = val

    # and print a summary
    print '--- Results summary ---'
    for i in range(nThreads):
        print 'Thread: {}'.format(i+1)
        print 'Query: {}'.format(res[i].rstrip())
        print 'Results: {}\n---'.format(summ[i].rstrip())

###
if __name__=="__main__":
    main()

### END ###
