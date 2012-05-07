QVis.HeatMap = function(rootid,opts) {
	QVis.Graph.call(this,rootid,opts);

	//unique to scatterplots
	this.rectcontainer = null;
}

//inherit Graph Object
QVis.HeatMap.prototype = new QVis.Graph();

//fix constructor reference
QVis.HeatMap.constructor = QVis.HeatMap;

//to get access to the original functions
QVis.HeatMap.base = QVis.Graph.prototype;

//add a new render function
//data format: {'data':[{},{},...],'names':["","",...],'types':{"":,"":,...}}
QVis.HeatMap.prototype.render = function(_data, _labels,_types, opts) {
	this.selectx = false;
	this.selecty = false;
	this.selectz = true;
	//call the original render function
	var labelsfrombase = QVis.HeatMap.base.render.call(this,_data,_labels,_types,opts);

	// you should know why this is necessary
	var self = this;

	// create x,y axis scales
	var xdimname = ""+_labels.dimnames[1];
	var ydimname = ""+_labels.dimnames[0];
	console.log(xdimname+','+ydimname);
	console.log(_labels.dimbases[xdimname]);
	console.log(_labels.dimwidths[xdimname]);
	console.log(Number(_labels.dimwidths[xdimname]+_labels.dimbases[xdimname]));
	console.log(_labels.dimbases[ydimname]);
	console.log(_labels.dimwidths[ydimname]);
	console.log(Number(_labels.dimwidths[ydimname]+_labels.dimbases[ydimname]));
	var zscale = this.createScale(_data,_types,labelsfrombase.z_label,this.w,this.px,false,true).range(colorbrewer.Oranges[9]);
	var xscale = d3.scale.linear().domain([_labels.dimbases[xdimname],Number(_labels.dimwidths[xdimname])+Number(_labels.dimbases[xdimname])]).range([this.px,this.w-this.px]);
	var yscale = d3.scale.linear().domain([_labels.dimbases[ydimname],Number(_labels.dimwidths[ydimname])+Number(_labels.dimbases[ydimname])]).range([this.py,this.h-this.py]);
	console.log(xscale.domain());
	console.log(yscale.domain());
	console.log(xscale.range());
	console.log(yscale.range());

	this.svg = d3.selectAll(this.jsvg.get())
		.attr('width', this.w)
		.attr('height', this.h)
		.attr('class', 'g')
		.attr('id', 'svg_'+this.rootid);
				
	this.rectcontainer = this.svg.append('g')
		.attr("class", "rectcontainer")
		.attr("width", this.w-this.px)					
		.attr("height",  this.h-this.py)
		.attr("x", 0)
		.attr("y", 0);

	console.log("width:"+(self.w-2*self.px)/_labels.dimwidths[xdimname]);
	console.log("height:"+(self.h-2*self.py)/_labels.dimwidths[ydimname]);
	//just testing the rects function
	this.drawRects(this.rectcontainer,_data,_types,xscale,yscale,'dims.'+xdimname,'dims.'+ydimname,function(d){return Math.max(1,(self.w-2*self.px)/_labels.dimwidths[xdimname])},
		function(d){return Math.max(1,(self.h-2*self.py)/_labels.dimwidths[ydimname]);},
		function(d) {return zscale(d[labelsfrombase.z_label]);});

}
