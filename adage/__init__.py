import multiprocessing
import time
import networkx as nx
import subprocess
import glob
import adage.trackers
import logging
import os
import shutil
import sys
import dagstate

from decorators import adagetask,functorize,Rule, qualifiedname
from dagutils import *

log = logging.getLogger(__name__)

def validate_finished_dag(dag):
  for node in dag:
    nodeobj = dag.getNode(node)
    if nodeobj.submitted:
      sanity = all([nodeobj.submitted > dag.getNode(x).ready_by_time for x in dag.predecessors(node)])
      if not sanity:
        return False
  return True
    
def get_failure_info(backend,nodeobj):
  try:
    backend.result_of(nodeobj.result)
  except:
    log.info("node {} failed with error: {}".format(nodeobj,sys.exc_info()))

def nodes_left_or_rule(dag,rules):
  nodes_we_could_run = [node for node in dag.nodes() if not dagstate.upstream_failure(dag,dag.getNode(node))]
  nodes_running_or_defined = [x for x in nodes_we_could_run if dagstate.node_defined_or_waiting(dag.getNode(x))]

  if any(rule.applicable(dag) for rule in rules):
    return True

  log.debug('nodes we could run: {}'.format(nodes_we_could_run))
  if nodes_running_or_defined:
    log.debug('{} nodes that could be run or are running are left.'.format(len(nodes_running_or_defined)))
    log.debug('nodes are: {}'.format([dag.node[n] for n in nodes_running_or_defined]))
    return True
  else:
    log.info('no nodes can be run anymore')
    return False

def update_dag(dag,rules):
  #iterate rules in reverse so we can safely pop items
  for i,rule in reversed([x for x in enumerate(rules)]):
    if rule.applicable(dag):
      log.info('extending graph.')
      rule.apply(dag)
      rules.pop(i)
    else:
      log.debug('rule not ready yet')

def process_dag(dag,rules,backend):
  for node in nx.topological_sort(dag):
    nodeobj = dag.getNode(node)

    if not nodeobj.backend:
      nodeobj.backend = backend

    log.debug("working on node: {} with obj {}".format(node,nodeobj))

    if nodeobj.submitted:
      log.debug("node already submitted. continue")
      continue;
    if dagstate.upstream_ok(dag,nodeobj):
      log.info('submitting {} job'.format(nodeobj))
      nodeobj.result = backend.submit(nodeobj.task)
      submit_time = time.time()
      nodeobj.submitted = submit_time

    if dagstate.upstream_failure(dag,nodeobj):
      log.warning('not submitting node: {} due to upstream failure'.format(node))
  
def rundag(dag,rules, track = False, backend = None, loggername = None, workdir = None, trackevery = 1):
  if loggername:
    global log
    log = logging.getLogger(loggername)
  
  ## funny behavior of multiprocessing Pools means that
  ## we can not have backendsubmit = multiprocsetup(2)  in the function sig
  ## so we only initialize them here
  if not backend:
    from backends import MultiProcBackend
    backend = MultiProcBackend(2)

  if not workdir:
    workdir = os.getcwd()


  trackerlist = [trackers.SimpleReportTracker(log)]
  
  if track:
    trackerlist += [trackers.GifTracker(gifname = '{}/workflow.gif'.format(workdir), workdir = '{}/track'.format(workdir), mindelta = trackevery)]
    
  for t in trackerlist: t.initialize(dag)
  #while we have nodes that can be submitted
  while nodes_left_or_rule(dag,rules):
    update_dag(dag,rules)
    process_dag(dag,rules,backend)
    for t in trackerlist: t.track(dag)
    time.sleep(1)
    
  log.info('all running jobs are finished.')
  
  for node in dag.nodes():
    #check node status one last time so we pick up the finishing times
    dagstate.node_status(dag.getNode(node))
    
  for t in trackerlist: t.finalize(dag)

  if not validate_finished_dag(dag):
    log.error('DAG execution not validating')
    raise RuntimeError
  log.info('execution valid. (in terms of execution order)')
  
  if any(dag.getNode(x).state() == nodestate.FAILED for x in dag.nodes()):
    log.error('raising RunTimeError due to failed jobs')
    raise RuntimeError 
