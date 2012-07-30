var renderagg = null;
var current_tile = 0;
var current_zoom = 0;

// get these from backend
var max_zoom = 1;
var total_tiles = 1;
var total_tiles_root = 1;

var menutype;

$(document).ready(function() {
	$('#sql-query-submit').on('click',user_query_handler);
	$('#button-up').on('click',move_up);
	$('#button-down').on('click',move_down);
	$('#button-left').on('click',move_left);
	$('#button-right').on('click',move_left);
	$('#button-zoom-out').on('click',zoom_out);
	var buttons = $('.button');
	console.log(buttons);
	$('.nav-button').button();
	console.log(buttons);	

	function move_up() {
		var tile = current_tile - total_tiles_root;
		if(tile< 0){
			tile= 0;
		}
		$.getJSON('/fetch-tile',{tile_id: tile,level:current_zoom},function(jsondata){
			console.log(jsondata);
			redraw_graph(jsondata);
		});
		console.log(current_tile+","+current_zoom+"-->"+tile+","+zoom);
		current_tile = tile;
		return false;
	}

	function move_down() {
		var tile = current_tile + total_tiles_root;
		if(tile>= total_tiles){
			tile= total_tiles-1;
		}
		$.getJSON('/fetch-tile',{tile_id: tile,level:current_zoom},function(jsondata){
			console.log(jsondata);
			redraw_graph(jsondata);
		});
		console.log(current_tile+","+current_zoom+"-->"+tile+","+zoom);
		current_tile = tile;
		return false;
	}

	function move_left() {
		var tile = current_tile;
		if((tile % total_tiles_root) != total_tiles-1){
			tile = tile + 1;
		}
		$.getJSON('/fetch-tile',{tile_id: tile,level:current_zoom},function(jsondata){
			console.log(jsondata);
			redraw_graph(jsondata);
		});
		console.log(current_tile+","+current_zoom+"-->"+tile+","+zoom);
		current_tile = tile;
		return false;
	}

	function move_right() {
		var tile = current_tile;
		if((tile % total_tiles_root) != 0){
			tile = tile - 1;
		}
		$.getJSON('/fetch-tile',{tile_id: tile,level:current_zoom},function(jsondata){
			console.log(jsondata);
			redraw_graph(jsondata);
		});
		console.log(current_tile+","+current_zoom+"-->"+tile+","+zoom);
		current_tile = tile;
		return false;
	}

	function zoom_out() {
		var zoom = current_zoom - 1;
		var tile = 0;
		if(zoom < 0) {
			zoom = 0;
		} else { // compute zoom out index
			var total_tiles_root_root = Math.sqrt(total_tiles_root);
			var xind = Math.floor(current_tile/total_tiles_root)/total_tiles_root_root;
			var yind = Math.floor(current_tile % total_tiles_root)/total_tiles_root_root;
			tile = xind*total_tiles_root_root+yind;
		}
		$.getJSON('/fetch-tile',{tile_id: tile,level:zoom},function(jsondata){
			console.log(jsondata);
			redraw_graph(jsondata);
		});
		console.log(current_tile+","+current_zoom+"-->"+tile+","+zoom);
		current_tile = tile;
		current_zoom = zoom;
		return false;
	}

	function zoom_in() {
		tile = Number($('#zoom-in-text').val());
		zoom = current_zoom + 1;
		if(zoom > max_zoom) {
			zoom = max_zoom;
		}
		if(tile < 0) {
			tile = 0;
		} else if (tile >= total_tiles) {
			tile = total_tiles - 1;
		}
		$.getJSON('/fetch-tile',{tile_id: tile,level:zoom},function(jsondata){
			console.log(jsondata);
			redraw_graph(jsondata);
		});
		console.log(current_tile+","+current_zoom+"-->"+tile+","+zoom);
		current_tile = tile;
		current_zoom = zoom;
		return false;
	}

	function user_query_handler() {
		max_zoom = QVis.DEFAULT_MAX_ZOOM;
		num_tiles = 1;
		console.log('made it here');
		if(renderagg) {
			renderagg.clear();
		}
		querytext = $('#sql-query-text').val();
		$.getJSON('/fetch-first-tile',{query: querytext},function(jsondata){
			console.log(jsondata);
			$('#resulting-plot-header').addClass('show');
			$('#aggplot').addClass('show');
			draw_graph(jsondata);
		});
		return false;
	}

	function redraw_graph(jsondata){
		var opts = {overlap:-0, r:1.5};
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

		max_zoom = jsondata['max_zoom'];
		total_tiles = jsondata['total_tiles'];
		total_tiles_root = jsondata['total_tiles_root'];
		console.log(max_zoom+","+total_tiles+","+total_tiles_root);
		renderagg.mini_render(data, labels,types);
	}

	function draw_graph(jsondata) {
		menutype = $('#vis-type-menu').val();
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

		max_zoom = jsondata['max_zoom'];
		total_tiles = jsondata['total_tiles'];
		total_tiles_root = jsondata['total_tiles_root'];
		console.log(max_zoom+","+total_tiles+","+total_tiles_root);
		renderagg.render(data, labels,types);
	}
});
