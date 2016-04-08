import adage
import adage.dagstate
from adage import adageop, Rule

#import some task functions that we'd like to run
from physicstasks import prepare, download, rivet, pythia, plotting, mcviz

import logging
logging.basicConfig(level=logging.INFO)

@adageop
def download_done(adageobj):
    #we can only run pythia once the donwload is done and we know hoe many LHE files we have
    download_node = adageobj.dag.getNodeByName('download')
    if download_node:
        return adage.dagstate.node_status(download_node)
    return False
    
@adageop
def schedule_pythia(adageobj):
    
    download_node = adageobj.dag.getNodeByName('download')
    lhefiles = download_node.result

    #let's run pythia on these LHE files
    pythia_nodes = [adageobj.dag.addTask(pythia.s(lhefilename = lhe), depends_on = [download_node]) for lhe in lhefiles]

    # we already know what the pythia result will look like so we don't need to wait for the nodes to run
    # to schedule them
    hepmcfiles        = [x.rsplit('.lhe')[0]+'.hepmc' for x in lhefiles]

    adageobj.dag.addTask(mcviz.s(hepmcfile = hepmcfiles[0]), depends_on = pythia_nodes[0:1])

    #Rivet and then produce some plots.
    rivet_node        = adageobj.dag.addTask(rivet.s(workdir = 'here', hepmcfiles = hepmcfiles), depends_on = pythia_nodes)
    adageobj.dag.addTask(plotting.s(workdir = 'here', yodafile = 'Rivet.yoda'), depends_on = [rivet_node])
        
def build_initial_dag():
    adageobj = adage.adageobject()

    prepare_node    = adageobj.dag.addTask(prepare.s(workdir = 'here'))
    adageobj.dag.addTask(download.s(workdir = 'here'), depends_on = [prepare_node], nodename = 'download')

    #possible syntax that could be nice using partial function execution
    #    download_node = do(download.s(workdir = 'here'), depends_on = [prepare_node], nodename = 'download')

    adageobj.rules = [ Rule(download_done.s(), schedule_pythia.s()) ]
    return adageobj
    
def main():
    adageobj = build_initial_dag()
    adage.rundag(adageobj, track = True, trackevery = 5)

if __name__=='__main__':
    main()