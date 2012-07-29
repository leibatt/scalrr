var renderagg = null;

$(document).ready(function() {
	$('#sql-query-submit').on('click',user_query_handler);
	console.log("got here");
	$('.button').button({
		text: false,
		icons: {
			primary: 'ui-icon-plus'
		}
	});
	
	function user_query_handler() {
		console.log('made it here');
		if(renderagg) {
			renderagg.clear();
		}
		querytext = $('#sql-query-text').val();
		$.getJSON('/fetch-first-tile',{query: querytext},function(jsondata){
			console.log(jsondata);
			draw_graph(jsondata);
		});
		return false;
	}

	function draw_graph(jsondata) {
		var menutype = $('#vis-type-menu').val();
		var opts = {overlap:-0, r:1.5};
		switch(menutype) {
			case 'mapplot':
				renderagg = new QVis.MapPlot('aggplot', opts);
				break;
			case 'scatterplot':
				renderagg = new QVis.ScatterPlot('aggplot', opts);
				break;
			case 'heatmap':
				renderagg = new QVis.HeatMap('aggplot',opts);
				break;
			default:
				console.log('menu type not supported, using heatmap...');
				renderagg = new QVis.HeatMap('aggplot', opts);
		}
		
		var data = jsondata['data'];
		var labels={'names' : jsondata['names'],
                   'x' : jsondata['names'][0]['name'],
		   'y' : jsondata['names'][1]['name'],
		   'z' : '',
		   'dimbases':jsondata['dimbases'],
		   'dimwidths':jsondata['dimwidths'],
		   'dimnames':jsondata['dimnames']};
		var types = jsondata['types'];
		
		console.log(jsondata['dimbases']);
		console.log(jsondata['dimwidths']);

		renderagg.render(data, labels,types);
	}
});
