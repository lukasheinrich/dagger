#!/usr/bin/env python
import time
import os
import logging
import adage
import adage.nodestate
import adage.backends
from adage import adagetask, adageop ,Rule
try:
    from celery import Celery
except ImportError:
    pass

logging.basicConfig(level = logging.INFO)
log = logging.getLogger(__name__)

@adagetask
def mytask(one):
    log.info('sleeping for %s, pid: %s',one,os.getpid())
    time.sleep(one)

@adagetask
def tofail(one):
    print 'failing'
    time.sleep(one)
    import random
    if random.random() < 0.5: raise RuntimeError

@adageop
def predicate(adageobj,depnode):
    return depnode.state == adage.nodestate.SUCCESS
    
@adageop
def rulebody(adageobj,depnode):
    mapnodes = []
    for i in range(6):
        mapnodes += [adageobj.dag.addTask(mytask.s(3*i), depends_on = [depnode], nodename = 'map')]
    adageobj.dag.addTask(mytask.s(3), depends_on = mapnodes, nodename = 'reduce')


def main():
    backend = adage.backends.MultiProcBackend(2)

    adageobj = adage.adageobject()

    one = adageobj.dag.addTask(mytask.s(5), nodename = 'first')
    two = adageobj.dag.addTask(mytask.s(3), depends_on = [one], nodename = 'second')
    
    adageobj.rules = [Rule(predicate.s(depnode = two),rulebody.s(depnode = two))]
    
    try:
        adage.rundag(adageobj, backend = backend, track = True, workdir = 'simpleTrack', trackevery = 10)
    except RuntimeError:
        log.error('ERROR')

if __name__ == '__main__':
    main()