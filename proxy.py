'''
Copyright (c) 2011 Brian Beggs

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
from functools import partial
from threading import Lock

real_objects = {}
proxy_lock = Lock()

def synchronized(lock):
    '''Synchronization decorator, borrowed from http://wiki.python.org/moin/PythonDecoratorLibrary#Synchronization'''
    def decorator(func):
        def wraper(*args, **kwargs):
            lock.acquire()
            try:
                return func(*args, **kwargs)
            finally:
                lock.release()
            
        return wraper
    return decorator


@synchronized(proxy_lock)
def register_module(module_service_name, module):
    if module_service_name in real_objects:
        del real_objects[module_service_name]
    real_objects[module_service_name] = module

@synchronized(proxy_lock)    
def unregister_module(module_service_name, module):
    if module_service_name in real_objects and real_objects[module_service_name] == module:
        del real_objects[module_service_name]


def provide_proxy(original_class):
    ''' 
    Decorator used to initialize a class to be available via the proxy module 
    Modules may be accessed later by creating a project object with a service name
    eaual to the module + Class name.
    
    For example the Event class from the threading module would be found at:
        threading.Event
    The same way imports work.
    '''    
    orig_init = original_class.__init__
    
    def __init__(self, *args, **kwargs):
        register_module('.'.join([self.__module__, self.__class__.__name__]), self)
        orig_init(self, *args, **kwargs)
        
    original_class.__init__ = __init__
    return original_class
    
class ProxyObject(object):
    '''
    Use this proxy object to make calls to other modules.  Using the
    proxy objects prevents implementing modules from having to know about the state
    of other modules running in the system.
    
    Calling methods on the proxy object can be done either synchronously or 
    asynchronously.
    
    To call a method Synchronously just call the method on the proxy object the 
    same as you would as if calling the method on the actual object itself.
    
    To call a method asynchronously pass the following keyword arguments along
    with the method call:
        -callback_success - method called upon success.  Will return whatever is returned from the calling method
        -callback_failure - method called upon failure.  Will return a string with the failure message
    
    If a module is not registered but a method call is made to it, a ModuleUnavailableException
    will be thrown.
    
    If a module does not have the method that is attempting to be called a NoSuchMethodException
    will be thrown.
    '''
    def __init__(self, service_name):
        self._service_name = service_name
        
    def __getattr__(self, name):
        obj = real_objects.get(self._service_name)
        if obj is None:
            raise ModuleUnavailableException('no module currently registered for %s' %self._service_name)
        if hasattr(obj, name) is None:
            raise NoSuchMethodException('service %s does not respond to the method %s' %(self._service_name, name))
        
        return partial(self.call_proxy_method, name)
                
    def call_proxy_method(self, method_name, *args, **kwargs):
        if 'callback_success' in kwargs:
            self._call_async(method_name, *args, **kwargs)
        else:
            return self._call_sync(method_name, *args, **kwargs)

    def _call_async(self, method_name, *args, **kwargs):
        raise NotImplementedError('Asynchrnonous callbacks are not yet implemented')
    
    def _call_sync(self, method_name, *args, **kwargs):
        obj = real_objects.get(self._service_name)
        return getattr(obj, method_name)(*args, **kwargs)
        
class NoSuchMethodException(Exception):
    ''' Exception raised when calling a method on a proxy object that does not exist '''
class ModuleUnavailableException(Exception):
    ''' Exception raised when a call is made on a proxy object but the module is not registered '''    
        
