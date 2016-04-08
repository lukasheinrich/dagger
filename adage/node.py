import nodestate
import time
import uuid
import logging

log = logging.getLogger(__name__)

class Node(object):
    def __init__(self,name,task,identifier = None):
        self.identifier = identifier or str(uuid.uuid4())
        self.name = name

        self.task = task

        self.define_time = time.time()
        self.submit_time = None
        self.ready_by_time = None

        self._state = nodestate.DEFINED
        self.resultproxy = None
        self.backend = None

    def __repr__(self):
        return '<Node name: {} id: {} state: {}>'.format(self.name,self.identifier,self.state)

    def update_state(self):
        #if we do not have a result object
        #that means it's not submitted yet
        if not self.resultproxy:
            self._state = nodestate.DEFINED
            return
        
        #if we have a resultobject
        #but the result is not ready
        #the node is still running
        if not self.ready():
            self._state = nodestate.RUNNING
            return
            
        #if it's ready it's either successful
        #or failed
        if self.successful():
            self._state = nodestate.SUCCESS
            return
        else:
            self._state = nodestate.FAILED
            return
    
    @property
    def state(self):
        self.update_state()
        return self._state

    @property
    def result(self):
        return self.backend.result(self.resultproxy)
        
    def ready(self):
        if not self.resultproxy:
            return False

        ready = self.backend.ready(self.resultproxy)
        if not ready:
            return False

        if not self.ready_by_time:
            self.ready_by_time = time.time()
            log.info('node finished %s finished',self)
        return True

    def successful(self):
        if not self.resultproxy:
            return False
        return self.backend.successful(self.resultproxy)
