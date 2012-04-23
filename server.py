from gevent.pywsgi import WSGIServer # must be pywsgi to support websocket
from geventwebsocket.handler import WebSocketHandler
from flask import Flask, request, render_template, g, redirect
import random
import json
import md5
import traceback
import scidb_server_interface as sdbi
app = Flask(__name__)


@app.before_request
def before_request():
    """Make sure we are connected to the database each request."""
    sdbi.scidbOpenConn()

@app.teardown_request
def teardown_request(exception):
    """Closes the database again at the end of the request."""
    sdbi.scidbCloseConn()

@app.route('/', methods=["POST", "GET"])
def index():
    return 'hello world'


@app.route('/index/', methods=["POST", "GET"])
def get_data():
    query = ""
    if request.method == 'POST':
        query = str(request.form['text'])
    queryresultarr = query_execute(query)
    #print queryresultarr['data']
    return render_template('index.html',
                           data=queryresultarr['data'],
                           labels={'gbs' : queryresultarr['names'],
                                   'x' : queryresultarr['names'][0],
				   'y' : queryresultarr['names'][0],
                                   'aggs' : queryresultarr['names'],
                                   'id' : 'id'},
			   types=queryresultarr['types'])

@app.route('/index2/', methods=["POST", "GET"])
def get_data2():
    return render_template('index2.html')

@app.route('/json-data', methods=["POST", "GET"])
def get_data_ajax():
    print "got json request"
    query = request.args.get('query',"",type=str)
    queryresultarr = query_execute(query)
    print json.dumps(queryresultarr)
    return json.dumps(queryresultarr)

def query_execute(userquery):
	query = "select * from earthquake3"
	if userquery != "":
		query = userquery
	print query
	qpresults = sdbi.verifyQuery(query,False)
	queryresult = sdbi.executeQuery(query,qpresults,False,False,sdbi.RESTYPE['AGGR'],10) # ignore reduce_type for now
	queryresultarr = sdbi.getAllAttrArrFromQueryForJSON(queryresult,qpresults['names'])
	return queryresultarr






if __name__ == "__main__":
    app.debug = True
    address = ('', 8080)
    http_server = WSGIServer(address, app, handler_class=WebSocketHandler)
    print "server is running now"
    http_server.serve_forever()
