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

//to get access to the original functions
QVis.ScatterPlot.base = QVis.Graph.prototype;

//add a new render function
//data format: {'data':[{},{},...],'names':["","",...],'types':{"":,"":,...}}
QVis.ScatterPlot.prototype.render = function(_data, _labels,_types, opts) {
	this.selectx = true;
	this.selecty = true;
	this.selectz = true;

	this.draw_obj = "circle";
	//call the original render function
	var labelsfrombase = QVis.ScatterPlot.base.render.call(this,_data,_labels,_types,opts);
	console.log("z_label "+labelsfrombase.z_label);

	var self = this;

	// create x,y axis scales
	var xscale = this.createScale(_data,_types,labelsfrombase.x_label,this.w,this.px,false,false);
	var yscale = this.createScale(_data,_types,labelsfrombase.y_label,this.h,this.py,true,false);
	var zscale = this.createScale(_data,_types,labelsfrombase.z_label,0,0,false,true)
			.range(colorbrewer.Oranges[9]);
	console.log("xscale domain: "+xscale.domain());
	console.log("zscale range: "+zscale.range());

	this.svg = d3.selectAll(this.jsvg.get())
		.attr('width', this.w)
		.attr('height', this.h)
		.attr('class', 'g')
		.attr('id', 'svg_'+this.rootid);
	this.add_axes(xscale, yscale,labelsfrombase.x_label,labelsfrombase.y_label, self.strings,_types);
				
	this.circlecontainer = this.svg.append('g')
		.attr("class", "circlecontainer")
		.attr("width", this.w-this.px)					
		.attr("height",  this.h-this.py)
		.attr("x", 0)
		.attr("y", 0);

	this.drawCircles(this.circlecontainer,_data,_types,xscale,yscale,labelsfrombase.x_label,labelsfrombase.y_label,this.defaultRadius,function(d) {return zscale(d[labelsfrombase.z_label]);});
	//just testing the rects function
	//this.drawRects(this.circlecontainer,_data,_types,xscale,yscale,labelsfrombase.x_label,labelsfrombase.y_label,this.defaultRadius,this.defaultRadius,this.defaultColor);

	this.add_brush(xscale,yscale,labelsfrombase.x_label,labelsfrombase.y_label,function(d) {return zscale(d[labelsfrombase.z_label]);},this.circlecontainer);

}
