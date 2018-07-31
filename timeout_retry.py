import asyncio
import logging
 

 # The default timeout to use for requests. Worst case: Requesting threshold 4-4 takes at least 1.8s
DEFAULT_TIMEOUT_MSEC = 3500 
 
 
class TimeoutRetryHandler(object):
    """
    Manages timeout and retry logic for an LCN request.
    """
    def __init__(self, loop, num_tries = 3, timeout_msec = DEFAULT_TIMEOUT_MSEC):
        """
        Constructor.
       
        @param numTries the maximum number of tries until the request is marked as failed (-1 means forever)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
 
        self.loop = loop
        self.num_tries = num_tries
        self._timeout_msec = timeout_msec
 
        self._timeout_handle = None
       
        self.reset()
    
    def is_active(self):
        """
        Checks whether the request logic is active.
        """
        return self._timeout_handle is not None
    
    def set_timeout_msec(self, timeout_msec):
        self._timeout_msec = timeout_msec
       
    def set_timeout_callback(self, func):
        """
        timeout_callback function is called, if timeout expires.
        Function has to take one argument:
            returns failed state (True if failed)
        """
        self._timeout_callback = func
 
    def on_timeout(self):
        if self._timeout_callback is not None:
            self._timeout_callback(self._num_tries_left == 0)
 
        if self._num_tries_left == 0:
            self.cancel()
            return
        elif self._num_tries_left > 0 :
            self._num_tries_left -= 1
        #print('Init next handle')
        self._timeout_handle = self.loop.call_later(self._timeout_msec/1000, self.on_timeout)
 
    def reset(self):
        if self._timeout_handle is not None:
            self._timeout_handle.cancel()
            self._timeout_handle = None
        self._num_tries_left = 0
       
    def activate(self, timeout_callback = None):
        """
        Schedules the next request.
        """
        if self.is_active():
            return
        self.reset()
        self._num_tries_left = self.num_tries
        if timeout_callback is not None:
            self.set_timeout_callback(timeout_callback)
        self._timeout_handle = self.loop.call_soon(self.on_timeout)
   
    def cancel(self):
        """
        Must be called when a response (requested or not) has been received.
        """
        self.reset()
       
 
 
if __name__ == '__main__':
   
    def timeout_callback(num_retry):
        print('Execute... {:d}'.format(num_retry))
   
    loop = asyncio.get_event_loop()
    trh = TimeoutRetryHandler(loop, timeout_msec = 1000)
    trh.activate(timeout_callback)
    loop.call_later(0.5, lambda: print('Is active:', trh._is_active()))
    loop.call_later(1.5, trh.cancel)
    loop.call_later(2.0, lambda: print('Is active:', trh._is_active()))
   
    loop.run_forever()