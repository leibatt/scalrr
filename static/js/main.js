var renderagg = null;

$(document).ready(function() {
	$('#sql-query-submit').on('click',user_query_handler);
	$('#reduce-type-form-submit').on('click',function(){return false;});
	//$('#vis-type-menu').on('change',);
	
	function user_query_handler() {
		console.log('made it here');
		if(renderagg) {
			renderagg.clear();
		}
		querytext = $('#sql-query-text').val();
		resolution_lvl = $('#resolution-lvl-menu').val();
		dialogue(querytext);
		$.getJSON('/json-data',{query: querytext,resolution:resolution_lvl},function(jsondata){
			console.log(jsondata);
			if(jsondata['reduce_res']) { // query met reduce_res requirements
				var user_reduce_res = confirm('Query result will be large. Reduce resolution?');
				if(user_reduce_res) {
					$( "#dialog" ).dialog("open");
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

	function reduce(querytext,reduce_type,predicate) {
		options = {query: querytext, reduce_type: reduce_type,resolution:resolution_lvl};
		if(predicate) {
			options.predicate = predicate;
		}
		$.getJSON('/json-data-reduce',options,function(jsondata){
			console.log('jsondata: '+jsondata);
			draw_graph(jsondata);
		});
		return false;
	}

	function noreduce(querytext) {
		$.getJSON('/json-data-noreduction',{query: querytext},function(jsondata){
			console.log(jsondata);
			draw_graph(jsondata);
		});
		return false;
	}

	function draw_graph(jsondata) {
		var menutype = $('#vis-type-menu').val();
		var opts = {overlap:-0, r:1.5};
		var xlabel = jsondata['names'][0]['name'];
		var ylabel = jsondata['names'][1]['name'];
		switch(menutype) {
			case 'mapplot':
				renderagg = new QVis.MapPlot('aggplot', opts);
				xlabel = "attrs.lat";
				ylabel = "attrs.lon";
				break;
			case 'scatterplot':
				renderagg = new QVis.ScatterPlot('aggplot', opts);
				break;
			case 'heatmap':
				renderagg = new QVis.HeatMap('aggplot',opts);
				break;
			default:
				console.log('menu type not supported, using scatterplot...');
				renderagg = new QVis.ScatterPlot('aggplot', opts);
		}
		
		var data = jsondata['data'];
		var labels={'names' : jsondata['names'],
                   'x' : xlabel,
		   'y' : ylabel,
		   'z' : '',
		   'max':jsondata['max'],
		   'min':jsondata['min'],
		   'dimbases':jsondata['dimbases'],
		   'dimwidths':jsondata['dimwidths'],
		   'dimnames':jsondata['dimnames']};
		var types = jsondata['types'];
		console.log(['dimbases',jsondata['dimbases']]);
		console.log(['dimwidths',jsondata['dimwidths']]);
		$('#aggplot').addClass('show');
		renderagg.render(data, labels,types,opts);
	}

	function dialogue(querytext) {
		console.log("querytext:"+this.querytext);
		$( "#dialog" ).dialog({
			modal: true,
			autoOpen: false,
			closeOnEscape:false,
			open: function() {
				$("#reduce-type-menu").val('AGGR'); // set first element back to AGGR
				$('#reduce-type-filter-predicate').val(''); // clear predicate value
			},
			create:function(){
				// set the dialog to be visible
				$('#reduce-type-form').css('visibility','visible');
				
				(function() {
					$("#reduce-type-menu").change(function() { //reduce-type-special
						var reduce_type = $(this).val();
						$('#reduce-type-special').attr('class',reduce_type);
						console.log("inner function reduce type: "+reduce_type);
					});
				})();
			},
			buttons: {
				"Reduce Res":function() {
					var reduce_type = $('#reduce-type-menu').val();
					console.log("reduce_type: "+reduce_type);
					var predicate = $('#reduce-type-filter-predicate').val();
					$(this).dialog("close");
					//call reduce function from here
					reduce(querytext,reduce_type,predicate);
				},
				Cancel:function() {
					$(this).dialog("close");
					noreduce(querytext);	
				}
			}
		});
	}
});
