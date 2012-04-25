var renderagg = null;

$(document).ready(function() {
	$('#sql-query-submit').on('click',user_query_handler);
	
	function user_query_handler() {
		querytext = $('#sql-query-text').val();
		dialogue(querytext);
		//options: {query:'query to execute'}
		$.getJSON('/json-data',{query: querytext},function(jsondata){
			console.log(jsondata);
			if(jsondata['reduce_res']) { // query met reduce_res requirements
				var user_reduce_res = confirm('Query result will be large. Reduce resolution?');
				if(user_reduce_res) {
					$( "#dialog" ).dialog("open");
					//var reduce_type = prompt('Resolution reduction type (agg,sample,filter):','agg');
				} else { // run original query
					console.log("running original query");
					noreduce(querytext);
				}
				return false;
			}
			draw_graph(jsondata);

		});
		return false;
	}

	function reduce(querytext,reduce_type) {
		//options: {query:'query to execute'}
		$.getJSON('/json-data-reduce',{query: querytext,reduce_type: reduce_type},function(jsondata){
			console.log(jsondata);
			draw_graph(jsondata);
		});
		return false;
	}

	function noreduce(querytext) {
		//options: {query:'query to execute'}
		$.getJSON('/json-data-noreduction',{query: querytext},function(jsondata){
			console.log(jsondata);
			draw_graph(jsondata);
		});
		return false;
	}

	function draw_graph(jsondata) {
		var opts = {overlap:-0, r:1.5};
		renderagg = new QVis.ScatterPlot('aggplot', opts);
		var data = jsondata['data'];
		var labels={'gbs' : jsondata['names'],
                   'x' : jsondata['names'][0],
		   'y' : jsondata['names'][0],
                   'aggs' : jsondata['names']};
		var types = jsondata['types'];
		renderagg.render(data, labels,types);	
	}

	function dialogue(querytext) {
			console.log("querytext:"+this.querytext);
			$( "#dialog" ).dialog({
				modal: true,
				autoOpen: false,
				create:function(){$('#reduce-type-form').css('visibility','visible');},
				buttons: {
					"Reduce Res":function() {
						var reduce_type = $('#reduce-type-menu').val();
						console.log("reduce_type: "+reduce_type);
						$(this).dialog("close");
						//call reduce function from here
						reduce(querytext,reduce_type);
					},
					Cancel:function() {
						$(this).dialog("close");
						noreduce(querytext);	
					}
				}
			});
	}
});
