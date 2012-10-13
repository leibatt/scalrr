var renderagg = null;
var current_x = 0;
var current_y = 0;
var current_zoom = 0;
var flip = true; // whether we need to do inverted moves

// get these from backend
var max_zoom = 1;
var total_tiles = 1;
var total_xtiles = 1;
var total_ytiles = 1;
var total_tiles_root = 1;
var zoom_diff = 2;
var future_xtiles= 1;
var future_ytiles = 1;
var future_xtiles_exact = 1;
var future_ytiles_exact= 1;

var menutype;
var once =0;

$(document).ready(function() {
	$('#sql-query-submit').on('click',user_query_handler);
	$('#button-up').on('click',move_up);
	$('#button-down').on('click',move_down);
	$('#button-left').on('click',move_left);
	$('#button-right').on('click',move_right);
	//$('#button-zoom-out').on('click',zoom_out);
	//$('#button-zoom-in').on('click',zoom_in);
	$('.nav-button').button();

	function move_up() {
		if(flip && renderagg.inv[1]) {
			flip = false;
			return move_down();
		} else {
			flip = true;
		}
		var x = current_x;
		var y = current_y;
		var zoom = current_zoom;
		y = y - 1;
		if(y< 0){
			y= 0;
		}
		$.getJSON('/fetch-tile',{tile_xid: x,tile_yid:y,level:zoom,
					x_label:renderagg.labelsfrombase.x_label,y_label:renderagg.labelsfrombase.y_label},function(jsondata){
			console.log(jsondata);
			redraw_graph(jsondata);
		});
		console.log("move up:"+current_x+","+current_y+","+current_zoom+"-->"+x+","+y+","+zoom);
		current_y = y;
		return false;
	}

	function move_down() {
		if(flip && renderagg.inv[1]) {
			flip = false;
			return move_up();
		} else {
			flip = true;
		}
		var x = current_x;
		var y = current_y;
		var zoom = current_zoom;
		y = y + 1;
		if(y >= total_ytiles){
			y = total_ytiles-1;
		}
		$.getJSON('/fetch-tile',{tile_xid: x,tile_yid:y,level:zoom,
					x_label:renderagg.labelsfrombase.x_label,y_label:renderagg.labelsfrombase.y_label},function(jsondata){
			console.log(jsondata);
			redraw_graph(jsondata);
		});
		console.log("move down:"+current_x+","+current_y+","+current_zoom+"-->"+x+","+y+","+zoom);
		current_y = y;
		return false;
	}

	function move_left() {
		if(flip && renderagg.inv[0]) {
			flip = false;
			return move_right();
		} else {
			flip = true;
		}
		var x = current_x;
		var y = current_y;
		var zoom = current_zoom;
		x = x - 1;
		if(x < 0){
			x= 0;
		}
		$.getJSON('/fetch-tile',{tile_xid: x,tile_yid:y,level:zoom,
					x_label:renderagg.labelsfrombase.x_label,y_label:renderagg.labelsfrombase.y_label},function(jsondata){
			console.log(jsondata);
			redraw_graph(jsondata);
		});
		console.log("move left:"+current_x+","+current_y+","+current_zoom+"-->"+x+","+y+","+zoom);
		current_x = x;
		return false;
	}

	function move_right() {
		if(flip && renderagg.inv[0]) {
			flip = false;
			return move_left();
		} else {
			flip = true;
		}
		var x = current_x;
		var y = current_y;
		var zoom = current_zoom;
		x = x + 1;
		if(x >= total_xtiles){
			x = total_xtiles-1;
		}
		$.getJSON('/fetch-tile',{tile_xid: x,tile_yid:y,level:zoom,
					x_label:renderagg.labelsfrombase.x_label,y_label:renderagg.labelsfrombase.y_label},function(jsondata){
			console.log(jsondata);
			redraw_graph(jsondata);
		});
		console.log("move right: "+current_x+","+current_y+","+current_zoom+"-->"+x+","+y+","+zoom);
		current_x = x;
		return false;
	}

	function zoom_out() {
		var x = current_x;
		var y = current_y;
		var zoom = current_zoom;
		zoom = zoom - 1;
		if(zoom < 0){
			zoom = 0;
		}
		x = Math.floor(x/zoom_diff);
		y = Math.floor(y/zoom_diff);
		if(zoom != current_zoom) { // if we're actually going somewhere else
			$.getJSON('/fetch-tile',{tile_xid: x,tile_yid:y,level:zoom,
					x_label:renderagg.labelsfrombase.x_label,y_label:renderagg.labelsfrombase.y_label},function(jsondata){
				console.log(jsondata);
				redraw_graph(jsondata);
			});
			console.log("zoom out: "+current_x+","+current_y+","+current_zoom+"-->"+x+","+y+","+zoom);
			current_y = y;
			current_x = x;
			current_zoom = zoom;
		}
		return false;
	}

	function zoom_in() {
		tile_coords = $('#zoom-in-text').val();
		xy = tile_coords.split(",");
		x_offset= Number(xy[0]);
		y_offset= Number(xy[1]);
		if(x_offset < 0) {
			x_offset = 0;
		} else if (x_offset >= future_xtiles) {
			x_offset = future_xtiles - 1;
		}
		if(y_offset < 0) {
			y_offset = 0;
		} else if (y_offset >= future_ytiles) {
			y_offset = future_ytiles - 1;
		}
		if(renderagg.inv[0]) {
			x_offset = future_xtiles - x_offset - 1;
		}
		if(renderagg.inv[1]) {
			y_offset = future_ytiles - y_offset - 1;
		}
		
		var x = current_x * zoom_diff + x_offset;
		var y = current_y * zoom_diff + y_offset;
		zoom = current_zoom + 1;
		if(zoom >= max_zoom) {
			zoom = max_zoom - 1;
		}
		if(zoom != current_zoom) { // if we're actually going somewhere else
			$.getJSON('/fetch-tile',{tile_xid: x,tile_yid:y,level:zoom,
					x_label:renderagg.labelsfrombase.x_label,y_label:renderagg.labelsfrombase.y_label},function(jsondata){
				console.log(jsondata);
				redraw_graph(jsondata);
			});
			console.log("zoom in: "+current_x+","+current_y+","+current_zoom+"-->"+x+","+y+","+zoom);
			current_y = y;
			current_x = x;
			current_zoom = zoom;
		}
		return false;
	}

	function zoom_in2(x_offset,y_offset) {
		if(x_offset < 0) {
			x_offset = 0;
		} else if (x_offset >= future_xtiles) {
			x_offset = future_xtiles - 1;
		}
		if(y_offset < 0) {
			y_offset = 0;
		} else if (y_offset >= future_ytiles) {
			y_offset = future_ytiles - 1;
		}
		if(renderagg.inv[0]) {
			x_offset = future_xtiles - x_offset - 1;
		}
		if(renderagg.inv[1]) {
			y_offset = future_ytiles - y_offset - 1;
		}
		
		var x = current_x * zoom_diff + x_offset;
		var y = current_y * zoom_diff + y_offset;
		zoom = current_zoom + 1;
		if(zoom >= max_zoom) {
			zoom = max_zoom - 1;
		}
		if(zoom != current_zoom) { // if we're actually going somewhere else
			$.getJSON('/fetch-tile',{tile_xid: x,tile_yid:y,level:zoom,
					x_label:renderagg.labelsfrombase.x_label,y_label:renderagg.labelsfrombase.y_label},function(jsondata){
				console.log(jsondata);
				redraw_graph(jsondata);
			});
			console.log("zoom in: "+current_x+","+current_y+","+current_zoom+"-->"+x+","+y+","+zoom);
			current_y = y;
			current_x = x;
			current_zoom = zoom;
		}
		return false;
	}

	function user_query_handler() {
		max_zoom = QVis.DEFAULT_MAX_ZOOM;
		num_tiles = 1;
		once = 0;
		if(renderagg) {
			renderagg.clear();
		}
		querytext = $('#sql-query-text').val();
		resolution_lvl = $('#resolution-lvl-menu').val();
		console.log("resolution: "+resolution_lvl);
		$.getJSON('/fetch-first-tile',{query: querytext,data_threshold:resolution_lvl},function(jsondata){
			console.log(jsondata);
			$('#resulting-plot-header').addClass('show');
			$('#aggplot').addClass('show');
			draw_graph(jsondata);
		});
		return false;
	}

	function redraw_graph(jsondata){
		// preserve existing labels
		var x_label = renderagg.labelsfrombase.x_label;
		var y_label = renderagg.labelsfrombase.y_label;
		var z_label = renderagg.labelsfrombase.z_label;
		var opts = {overlap:-0, r:1.5};
		var data = jsondata['data'];
		var labels={'names' : jsondata['names'],
                   'x' : x_label,
		   'y' : y_label,
		   'z' : z_label,
		   'dimbases':jsondata['dimbases'],
		   'dimwidths':jsondata['dimwidths'],
		   'dimnames':jsondata['dimnames'],
		   'max':jsondata['max'],
		   'min':jsondata['min'],
		   'inv':renderagg.inv};
		var types = jsondata['types'];
		
		console.log(jsondata['dimbases']);
		console.log(jsondata['dimwidths']);

		max_zoom = jsondata['max_zoom'];
		total_tiles = jsondata['total_tiles'];
		total_xtiles = jsondata['total_xtiles'];
		total_ytiles = jsondata['total_ytiles'];
		future_xtiles_exact = jsondata['future_xtiles_exact'];
		future_ytiles_exact = jsondata['future_ytiles_exact'];
		total_tiles_root = jsondata['total_tiles_root'];
		future_xtiles = jsondata['future_xtiles'];
		future_ytiles = jsondata['future_ytiles'];
		console.log("max zoom, total tiles, total tiles root: "+max_zoom+","+total_tiles+","+total_tiles_root);
		console.log("total x/y tiles: ",total_xtiles+","+total_ytiles);
		console.log("future x/y tiles: ",future_xtiles+","+future_ytiles);

		if(once == 1) {
			once += 1;
			(function() {
				var mini_render = renderagg.mini_render;
				renderagg.mini_render = function(_data, _labels,_types, opts) {
					mini_render.apply(this,[_data, _labels,_types, opts]);
					$('svg rect').off();
					$('svg rect').unbind();
					renderagg.rectcontainer.selectAll('rect')
						.on("click",function(d,i){return check_zoom_in(d3.mouse(this));});

					$('svg rect')
						.bind("contextmenu",function(e) { return zoom_out();});
				}


			})();
		}
		renderagg.mini_render(data, labels,types);

/*
		renderagg.mini_render(data, labels,types);
		renderagg.rectcontainer.selectAll('rect')
			.on("click",function(d,i){return check_zoom_in(d3.mouse(this));});

		$('svg rect')
			.bind("contextmenu",function(e) { return zoom_out();});
*/
	}

	function draw_graph(jsondata) {
		menutype = $('#vis-type-menu').val();
		var opts = {overlap:-0, r:1.5};
		var use_dims = false;
		switch(menutype) {
			case 'mapplot':
				renderagg = new QVis.MapPlot('aggplot', opts);
				break;
			case 'scatterplot':
				renderagg = new QVis.ScatterPlot('aggplot', opts);
				break;
			case 'heatmap':
				renderagg = new QVis.HeatMap('aggplot',opts);
				use_dims = true;
				break;
			default:
				console.log('menu type not supported, using heatmap...');
				renderagg = new QVis.HeatMap('aggplot', opts);
				use_dims = true;
		}
		
		var data = jsondata['data'];

		// set x and y labels
		var x_label = jsondata['dimnames'][0];
		var y_label = x_label;
		if(use_dims) {
			x_label = jsondata['dimnames'][0];
			if(jsondata['dimnames'].length > 1) {
				y_label = jsondata['dimnames'][1];
			} else {
				y_label = x_label;
			}
		} else if(jsondata['names'].length > 0) {
			y_label = jsondata['dimnames'][1];
		}

		var labels={'names' : jsondata['names'],
                   'x' : x_label,
		   'y' : y_label,
		   'z' : '',
		   'dimbases':jsondata['dimbases'],
		   'dimwidths':jsondata['dimwidths'],
		   'dimnames':jsondata['dimnames'],
		   'max':jsondata['max'],
		   'min':jsondata['min']};
		var types = jsondata['types'];
		
		console.log(jsondata['dimbases']);
		console.log(jsondata['dimwidths']);

		zoom_diff = jsondata['zoom_diff'];
		max_zoom = jsondata['max_zoom'];
		total_tiles = jsondata['total_tiles'];
		total_tiles_root = jsondata['total_tiles_root'];
		total_xtiles = jsondata['total_xtiles'];
		total_ytiles = jsondata['total_ytiles'];
		future_xtiles_exact = jsondata['future_xtiles_exact'];
		future_ytiles_exact = jsondata['future_ytiles_exact'];
		future_xtiles = jsondata['future_xtiles'];
		future_ytiles = jsondata['future_ytiles'];
		console.log("max zoom, total tiles, total tiles root: "+max_zoom+","+total_tiles+","+total_tiles_root);

		if(once == 0){
			once += 1;
			(function() {
				var render = renderagg.render;
				renderagg.render = function(_data, _labels,_types, _opts) {
					render.apply(this,[_data, _labels,_types, _opts]);
					$('svg rect').off();
					$('svg rect').unbind();
					renderagg.rectcontainer.selectAll('rect')
						.on("click",function(d,i){return check_zoom_in(d3.mouse(this));});

					$('svg rect')
						.bind("contextmenu",function(e) { return zoom_out();});
				}


			})();
		}

		renderagg.render(data, labels,types);
	}

	function check_zoom_in(coords) {
		console.log(["coords:",coords]);
		// cut up the space according to the size of the tiles
		var width = 1.0*renderagg.w / future_xtiles_exact;
		var height = 1.0*renderagg.h / future_ytiles_exact;
		var xdim = 1.0*coords[0] - renderagg.px;
		var ydim = 1.0*coords[1] - renderagg.py;
		if(renderagg.inv[0]) {
			xdim = 1.0*renderagg.w - xdim;
		}
		if(renderagg.inv[1]){
			ydim= 1.0*renderagg.h-ydim;
		}

		var xindex = Math.floor(xdim / width);
		var yindex = Math.floor(ydim / height);
		console.log(["width",width,"height",height,"xdim",xdim,"ydim",ydim,"xindex",xindex,"yindex",yindex,"future_xtiles_exact",future_xtiles_exact,"future_ytiles_exact",future_ytiles_exact]);
		return zoom_in2(xindex,yindex);
	}
});
