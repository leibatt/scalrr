from gevent.pywsgi import WSGIServer # must be pywsgi to support websocket
from geventwebsocket.handler import WebSocketHandler
from flask import Flask, request, render_template, g, redirect
import random
import json
import md5
import traceback
import scidb_server_interface as sdbi
app = Flask(__name__)

saved_qpresults = 0

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
    print "got json request in init function"
    query = request.args.get('query',"",type=str)
    options = {'reduce_res_check':True}
    queryresultarr = query_execute(query,options)
    #print queryresultarr
    #print json.dumps(queryresultarr)
    return json.dumps(queryresultarr)

@app.route('/json-data-noreduction', methods=["POST", "GET"])
def get_data_ajax_noreduction():
    print "got json request in noreduce function"
    query = request.args.get('query',"",type=str)
    options = {'reduce_res_check':False}
    queryresultarr = query_execute(query,options)
    print "result length: ",len(queryresultarr['data'])
    #print json.dumps(queryresultarr)
    return json.dumps(queryresultarr)

@app.route('/json-data-reduce', methods=["POST", "GET"])
def get_data_ajax_reduce():
    print "got json request in reduce function"
    query = request.args.get('query',"",type=str)
    reduce_type = request.args.get('reduce_type',"",type=str)
    options = {'reduce_res_check':False,'reduce_res':True,'reduce_type':reduce_type}
    queryresultarr = query_execute(query,options)
    print "result length: ",len(queryresultarr['data'])
    #print queryresultarr
    #print json.dumps(queryresultarr)
    return json.dumps(queryresultarr)

#options: {reduce_res_check:True/False}
def query_execute(userquery,options):
	global saved_qpresults
	query = "select * from earthquake3"
	if userquery != "":
		query = userquery
		print query
	sdbioptions = {'afl':False}
	if saved_qpresults == 0:
		saved_qpresults = sdbi.verifyQuery(query,sdbioptions)
		#only do this check for new queries
		if options['reduce_res_check'] and (saved_qpresults['size'] > sdbi.D3_DATA_THRESHOLD):
			return {'reduce_res':True}
	if 'reduce_type' in options: # reduction requested
		sdbioptions['reduce_res'] = True
		sdbioptions['reduce_options'] = setup_reduce_type(options['reduce_type'],{'afl':False})
	else: #return original query
		sdbioptions = {'afl':False,'reduce_res':False}
	queryresult = sdbi.executeQuery(query,sdbioptions)

	sdbioptions={'dimnames':saved_qpresults['dims']}
	queryresultarr = sdbi.getAllAttrArrFromQueryForJSON(queryresult,sdbioptions)
	print "setting saved_qpresults to 0"
	saved_qpresults = 0 # reset so we can use later
	return queryresultarr

#returns necessary options for reduce type
#options: {'afl':True/False, 'predicate':"boolean predicate",'probability':double,'chunkdims':[]}
#required options: afl, predicate (if filter specified)
#TODO: make these reduce types match the scidb interface api reduce types
def setup_reduce_type(reduce_type,options):
	global saved_qpresults
	returnoptions = {'qpresults':saved_qpresults,'afl':options['afl']}
	returnoptions['reduce_type'] = sdbi.RESTYPE[reduce_type]
	#if reduce_type == 'agg':
	if 'chunkdims' in options:
		returnoptions['chunkdims'] = chunkdims
		#returnoptions['reduce_type'] = sdbi.RESTYPE['AGGR']
	#elif reduce_type == 'sample':
	if 'probability' in options:
		returnoptions['probability'] = options['probability']
		#returnoptions['reduce_type'] = sdbi.RESTYPE['SAMPLE']
	#elif reduce_type == 'filter':
	if 'predicate' in options:
		returnoptions['predicate'] = options['predicate']
		#returnoptions['reduce_type'] = sdbi.RESTYPE['FILTER']
	#else: #unrecognized type
	#	raise Exception("Unrecognized reduce type passed to the server.")
	return returnoptions


if __name__ == "__main__":
    app.debug = True
    address = ('', 8080)
    http_server = WSGIServer(address, app, handler_class=WebSocketHandler)
    print "server is running now"
    http_server.serve_forever()
