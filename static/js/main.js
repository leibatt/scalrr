var renderagg = null;

$(document).ready(function() {
	$('#sql-query-submit').on('click',function() {
		var querytext = $('#sql-query-text').val();
		$.getJSON('/json-data',{query: querytext},function(jsondata){
			var opts = {overlap:-0, r:1.5};
			renderagg = new QVis.ScatterPlot('aggplot', opts);
			console.log(jsondata);
			var data = jsondata['data'];
			var labels={'gbs' : jsondata['names'],
                           'x' : jsondata['names'][0],
			   'y' : jsondata['names'][0],
                           'aggs' : jsondata['names']};
			var types = jsondata['types'];
			renderagg.render(data, labels,types);	
		});
		return false;
	});
});
