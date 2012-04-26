QVis.ScatterPlot = function(rootid,opts) {
	QVis.Graph.call(this,rootid,opts);

	//unique to scatterplots
	this.circlecontainer = null;
	this.r = opts.r || 1.5;
}

//inherit Graph Object
QVis.ScatterPlot.prototype = new QVis.Graph();

//fix constructor reference
QVis.ScatterPlot.constructor = QVis.ScatterPlot;

//add a new render function
//data format: {'data':[{},{},...],'names':["","",...],'types':{"":,"":,...}}
QVis.ScatterPlot.prototype.render = function(_data, _labels,_types, opts) {
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
	var xscale = this.createScale(_data,_types,x_label,this.w,this.px);
	var yscale = this.createScale(_data,_types,y_label,this.h,this.py);

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

	this.svg = d3.selectAll(this.jsvg.get())
		.attr('width', this.w)
		.attr('height', this.h)
		.attr('class', 'g')
		.attr('id', 'svg_'+this.rootid);
	this.add_axes(xscale, yscale,x_label,y_label, self.strings,_types);
				
	this.circlecontainer = this.svg.append('g')
		.attr("class", "circlecontainer")
		.attr("width", this.w-this.px)					
		.attr("height",  this.h-this.py)
		.attr("x", 0)
		.attr("y", 0);

	
	//
	// This code renders the actual points
	function add_circle () {
		//console.log("label: "+label);
		//console.log(_data[0]);
		//console.log(_data.length);
		// create the container

		var range = 1000;
		var steps = _data.length/range+1;
		for(var drawindex = 0; (drawindex < steps) && (drawindex*range < _data.length); drawindex++) {
			console.log("drawing range: "+drawindex*range+"-"+(drawindex*range+range));
			var data;
			if(drawindex*range+range > _data.length) {
				data = _data.slice(drawindex*range,_data.length)
			} else {
				data = _data.slice(drawindex*range,drawindex*range+range)
			}
			self.circlecontainer.selectAll('circle')
					.data(data)
				.enter().append('circle')
					.attr('cy', function(d) { return self.h-yscale(self.get_data_obj(d[y_label],_types[y_label]))})
					.attr('cx', function(d) { return xscale(self.get_data_obj(d[x_label],_types[x_label]))})
					.attr('r', 2)
					.attr('fill', 'red')
					.attr('label', x_label);
		}
	}
	add_circle();

}
