#!/usr/bin/env python
# encoding: utf-8
"""
Router.py

Created by mikepk on 2009-06-28.
Copyright (c) 2009 Michael Kowalchik. All rights reserved.
"""

import sys
import os  #, glob
import unittest
import re

from webob import Request, Response, exc

from routes import Mapper, request_config
# handle Mako's top level lookup
from mako import exceptions

import app.controllers
import project


class Router:
    '''router class for connecting controllers to URLs'''
    def __init__(self,application=None,routes=None):
        self.controllers = {}
        self.map = Mapper()
        # initialize Router
        if not routes:
            raise Exception("Route mapping required, please pass in a routing function to Router init.")
        routes(self.map)
        self.load()

    def load(self):
        '''Scans the controllers path and imports all controllers with a pybald name.'''

        controller_names = []
        for controller in app.controllers.__all__:
            #lowercase and strip 'Controller'
            controller_name = re.search('(\w+)Controller',controller).group(1).lower()
            controller_names.append(controller_name)
            self.controllers[controller_name]={'name':controller,'module':getattr(app.controllers,controller)}
        
        # register the controller module names
        # with the mapper, creates the internal regular
        # expressions
        self.map.create_regs(controller_names)

    def deferred_exception(self, func, exc_info):
        '''Function wrapper / closure to re-raise exceptions that occur too early to be displayed.'''
        def raise_deferred(environ,start_response):
            raise exc_info[0], exc_info[1], exc_info[2]
        return raise_deferred


    def __call__(self,environ,start_response):
        '''WSGI app, Router is called directly to actually route the url to the target'''
        req = Request(environ)

        #method override
        # for REST architecture, this allows a POST parameter of _method
        # to be used to override POST with alternate HTTP verbs (PUT,DELETE)
        old_method = None
        req.errors = 'ignore'
        if '_method' in req.POST:
            old_method = environ['REQUEST_METHOD']
            environ['REQUEST_METHOD'] = req.POST['_method'].upper()
            del req.POST['_method']
            if project.debug:
                print "Changing request method to %s" % environ['REQUEST_METHOD']


        # routes config object, this must be done on every request.
        # sets the mapper and allows link_to and redirect_to to
        # function on routes
        config = request_config()
        config.mapper = self.map
        config.environ = environ
        # defines the redirect method. In this case it generates a
        # Webob Response object with the location and status headers
        # set
        config.redirect = lambda url: Response(location=url,status=302)
        

        # debug print messages
        if project.debug:
            print '============= '+req.path+' =============='


        # use routes to match the url to a path
        # urlvars will contain controller + other non query
        # URL data
        urlvars = self.map.match(req.path)
        
        environ['REQUEST_METHOD'] = old_method
        if not urlvars: urlvars = {}

        req.urlvars = urlvars
        environ['urlvars'] = urlvars
        if urlvars:
            try:
                controller = urlvars["controller"]
                action = urlvars["action"]
                if project.debug:
                    for key in urlvars.keys():
                        print '''%s: %s''' % (key, urlvars[key])

                #methods starting with underscore can't be used as actions
                if re.match('^\_',action):
                    raise exc.HTTPNotFound("Invalid Action")
                    
                # create controller instance from controllers dictionary
                # using routes 'controller' returned from the match
                controller = getattr(self.controllers[controller]['module'], self.controllers[controller]['name'])()
                handler = getattr(controller,action)
                
            # only catch the KeyError/AttributeError for the controller/action search
            except (KeyError, AttributeError):
                raise exc.HTTPNotFound("Missing Controller or Action")

        # No URL vars means nothing matched in the mapper function
        else:
            raise exc.HTTPNotFound("No URL match")

        try:
            # call the action we determined from the mapper
            return handler(environ,start_response)

        # This is a mako 'missing template' exception
        except exceptions.TopLevelLookupException:
            raise exc.HTTPNotFound("Missing Template")
            
        except:
            # All other program errors get re-raised
            # like a 500 server error
            raise

                
class routerTests(unittest.TestCase):
    def setUp(self):
        pass

    def testMap(self):
        router = Router()

    def testRoute(self):
        pass

    def testLoad(self):
        pass
        
if __name__ == '__main__':
    unittest.main()