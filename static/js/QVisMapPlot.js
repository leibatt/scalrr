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

//to get access to the original functions
QVis.MapPlot.base = QVis.Graph.prototype;

//add a new render function
//data format: {'data':[{},{},...],'names':["","",...],'types':{"":,"":,...}}
QVis.MapPlot.prototype.render = function(_data, _labels,_types, opts) {
	this.selectx = true;
	this.selecty = true;
	//call the original render function
	var labelsfrombase = QVis.ScatterPlot.base.render.call(this,_data,_labels,_types,opts);

	// you should know why this is necessary
	var self = this;

	// create x,y axis scales
	var xscale = this.createScale(_data,_types,labelsfrombase.x_label,this.w,this.px,false,false);
	var yscale = this.createScale(_data,_types,labelsfrombase.y_label,this.h,this.py,true,false);

	// Create the Google Map…
	var map = new google.maps.Map(d3.select("#map div").node(), {
		zoom: 2,
		center: new google.maps.LatLng(37.76487, -122.41948),
		mapTypeId: google.maps.MapTypeId.TERRAIN
	});
	$('#map div').css('width', this.w+'px').css('height', this.h+'px');

	var overlay = new google.maps.OverlayView();

	// Add the container when the overlay is added to the map.
	overlay.onAdd = function() {
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
				var d = new google.maps.LatLng(data[labelsfrombase.x_label], data[labelsfrombase.y_label]);
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
