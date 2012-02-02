"""
Bottle-CouchDB is a plugin that integrates CouchDB with your Bottle
application. It automatically connects to a database at the beginning of a
request and passes the database handle to the route callback.

To automatically detect routes that need a CouchDB connection, the plugin
searches for route callbacks that require a `db` keyword argument
(which is configurable) and skips the routes that do not. This removes
and overhead for routes that don't need a CouchDB connection.

Usage example:

    import bottle
    from bottle.ext import couchdb

    app = bottle.Bottle()
    plugin = couchdb.Plugin('my_db', server_name='http://localhost:5984')
    app.install(plugin)

    @app.route('/show/:item')
    def show(item, db):
        try:
            document = db[item]
            return template('showitem', page=document)
        catch couchdb.ResourceNotFound:
            return bottle.HTTPError(404, "Page not found")

"""

__author__ = "Caleb Brown"
__version__ = '0.0.1'
__license__ = 'BSD'


### CUT HERE


import couchdb
import inspect
from bottle import PluginError
from couchdb.http import ResourceNotFound
from couchdb.client import Document


class CouchDBPlugin(object):
    ''' This plugin passes an couchdb database handle to route callbacks
    that accept a `db` keyword argument. If a callback does not expect
    such a parameter, no connection is made. You can override the database
    settings on a per-route basis. '''

    name = 'couchdb'
    api = 2

    def __init__(self, db_name, server_name='', keyword='db'):
        self.server_name = server_name
        self.db_name = db_name
        self.keyword = keyword

    def get_server(self, server_name=None):
        if server_name is None:
            server_name = self.server_name
        return couchdb.Server(server_name)

    def get_database(self, db_name=None, server=None, server_name=None):
        if db_name is None:
            db_name = self.db_name
        if server is None:
            server = self.get_server(server_name)

        if db_name not in server:
            db = server.create(db_name)
        else:
            db = server[db_name]

        return db

    def setup(self, app):
        for other in app.plugins:
            if not isinstance(other, CouchDBPlugin): continue
            if other.keyword == self.keyword:
                raise PluginError("Found another couchdb plugin with "\
                "conflicting settings (non-unique keyword).")

    def apply(self, callback, context):
        conf = context.config.get('couchdb') or {}
        server_name = conf.get('server_name', self.server_name)
        db_name = conf.get('db_name', self.db_name)
        keyword = conf.get('keyword', self.keyword)

        # Test if the original callback accepts a 'db' keyword.
        # Ignore it if it does not need a database handle.
        args = inspect.getargspec(context.callback)[0]
        if keyword not in args:
            return callback

        def wrapper(*args, **kwargs):
            # Connect to the couchdb
            couch = self.get_server(server_name)

            db = self.get_database(db_name=db_name, server=couch)

            # Add the connection handle as a keyword argument.
            kwargs[keyword] = db

            return callback(*args, **kwargs)

        # Replace the route callback with the wrapped one.
        return wrapper


    def close(self):
        pass


Plugin = CouchDBPlugin
