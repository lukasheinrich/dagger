import multiprocessing
import sys

class MultiProcBackend(object):
  def __init__(self,poolsize):
    self.pool = multiprocessing.Pool(poolsize)
  def submit(self,task):
    return self.pool.apply_async(task)
  def result_of(self,result):
    return result.get()
  def ready(self,result):
    return result.ready()
  def successful(self,result):
    if not self.ready(result): return False
    return result.successful()
  def fail_info(self,result):
    try:
      self.result_of(result)
    except:
      return sys.exc_info()
      
class CeleryBackend(object):
  def __init__(self,app):
    self.app = app
  def submit(self,task):
    self.app.set_current()
    return task.func.celery.apply_async(task.args,task.kwargs,throw = False)
  def result_of(self,result):
    return result.get()
  def ready(self,result):
    return result.ready()
  def successful(self,result):
    return result.successful()
  def fail_info(self,result):
    try:
      self.result_of(result)
    except:
      return sys.exc_info()
    
class DummyResult(object):    
  pass
  
class DummyBackend(object):
  def submit(self,task):
    return DummyResult()
  def result_of(self,result):
    return None
  def ready(self,result):
    return True
  def successful(self,result):
    return False
  def fail_info(self,result):
    return 'cannot give reason :( '