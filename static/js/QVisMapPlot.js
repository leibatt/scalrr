QVis.MapPlot = function(rootid,opts) {
	QVis.Graph.call(this,rootid,opts);

	//unique to scatterplots
	this.circlecontainer = null;
	this.r = opts.r || 1.5;
}

//inherit Graph Object
QVis.MapPlot.prototype = new QVis.Graph();

//fix constructor reference
QVis.MapPlot.constructor = QVis.MapPlot;

//add a new render function
//data format: {'data':[{},{},...],'names':["","",...],'types':{"":,"":,...}}
QVis.MapPlot.prototype.render = function(_data, _labels,_types, opts) {
	// user wants us to draw something, so we know we have data now
	//assumption: data is always presented with labels
	if (!_labels || typeof(_labels) == 'undefined') {
		QVis.error("Did not get any data to render!")
		return;
	}

	this.update_opts(opts); // if new options are passed, update the options

	//clear everything to get them ready for drawing
	this.jsvg = $("#"+this.rootid + " svg"),
	this.jlegend = $("#"+this.rootid+" .legend");
	this.xlabeldiv = $("#"+this.rootid+" .xlabel");	
	this.ylabeldiv = $("#"+this.rootid+" .ylabel");		
	this.jsvg.empty(); this.jlegend.empty(); this.xlabeldiv.empty(); this.ylabeldiv.empty();

	// you should know why this is necessary
	var self = this;

	//console.log("this.rootid: " + this.rootid+", self.rootid: "+self.rootid);
	//console.log("this == self?" + this === self);

	// _labels.aggs contains the columns that will be plotted on the y-axis
	// I iterate through each column and consolidate the points that would be rendered
	// This means that there could be overlapping points from two different columns
	var labels = _labels.aggs, 
		x_label = _labels.x,
		y_label = _labels.y,
		cscale = d3.scale.category10().domain(labels);  // color scale

	// create x,y axis scales
	var xscale = this.createScale(_data,_types,x_label,this.w,this.px,false);
	var yscale = this.createScale(_data,_types,y_label,this.h,this.py,true);

	//TODO: push the legend and menu features into the graph object
	// add the legend and color it appropriately
	var legend = d3.selectAll(this.jlegend.get()).selectAll('text')
			.data(labels)
		.enter().append('div')
			.style('float', 'left')
			.style('color', cscale)
			.text(String);		
	
	//
	// render x-axis select options
	var xaxisselect = this.xlabeldiv.append($("<select></select>")).find("select");
	var xaxislabel = d3.selectAll(xaxisselect.get()).selectAll("option")
			.data(_labels.gbs)
		.enter().append("option")
			.attr("value", String)
			.text(String);
	xaxisselect.val(x_label);
	console.log(_labels.gbs);
	//
	// render y-axis select options
	var yaxisselect = this.ylabeldiv.append($("<select></select>")).find("select");
	var yaxisattrselect = yaxisselect.append($('<optgroup label="attrs"></optgroup>')).find("optgroup");
	var yaxislabel = d3.selectAll(yaxisattrselect.get()).selectAll("option")
			.data(_labels.gbs)
		.enter().append("option")
			.attr("value", String)
			.text(String);
	yaxisselect.val(y_label);
	//
	// I create and execute this anonymous function so
	// selectedval will be private to and accessible by the .change() callback function
	// Manually set the new labels and call render_scatterplot again
	// 
	// notice that I use "self" instead of "this".
	//
	(function() {
		var selectedval = x_label;
		$("#"+self.rootid+" .xlabel select").change(function() {
			var val = $("#"+self.rootid+" .xlabel select").val();
			var yval = $("#"+self.rootid+" .ylabel select").val(); // should be the same as before
			console.log(["selected option", selectedval, val])				
			if (val == selectedval) return;
			selectedval = val;
			var newlabels = {"x" : val,"y": yval, "gbs" : _labels.gbs, "aggs" : _labels.aggs};

			self.render(_data, newlabels,_types, opts);
		});
	})();

	(function() {
		var selectedval = y_label;
		$("#"+self.rootid+" .ylabel select").change(function() {
			var val = $("#"+self.rootid+" .ylabel select").val();
			var xval = $("#"+self.rootid+" .xlabel select").val(); // should be the same as before
			console.log(["selected option", selectedval, val])				
			if (val == selectedval) return;
			selectedval = val;
			var newlabels = {"y" : val,"x": xval, "gbs" : _labels.gbs, "aggs" : _labels.aggs};

			self.render(_data, newlabels,_types, opts);
		});
	})();

	// Create the Google Map…
	var map = new google.maps.Map(d3.select("#map").node(), {
		zoom: 1,
		center: new google.maps.LatLng(37.76487, -122.41948),
		mapTypeId: google.maps.MapTypeId.TERRAIN
	});
	$('#map').css('width', 2*this.w+'px').css('height', 2*this.h+'px');

	var overlay = new google.maps.OverlayView();

	// Add the container when the overlay is added to the map.
	overlay.onAdd = function() {
		console.log("get here in overlay.onadd");
		var layer = d3.select(this.getPanes().overlayLayer).append("div")
		.attr("class", "stations");

		// Draw each marker as a separate SVG element.
		// We could use a single SVG, but what size would it have?
		overlay.draw = function() {
			var projection = this.getProjection(),
			  padding = 10;

			var marker = layer.selectAll("svg")
			  .data(_data)
			  .each(transform) // update existing markers
			.enter().append("svg:svg")
			  .each(transform)
			  .attr("class", "marker");

			// Add a circle.
			marker.append("svg:circle")
			  .attr("r", self.defaultRadius)
			  .attr("cx", padding)
			  .attr("cy", padding).attr('fill',self.defaultColor(null));

			function transform(data) {
				//LatLng(lat,lon)
				var d = new google.maps.LatLng(data[x_label], data[y_label]);
				//console.log(d.lat()+","+d.lng());
				d = projection.fromLatLngToDivPixel(d);
				return d3.select(this)
				    .style("left", (d.x - padding) + "px")
				    .style("top", (d.y - padding) + "px");
			}
		};
	};

	// Bind our overlay to the map…
	overlay.setMap(map);
}
