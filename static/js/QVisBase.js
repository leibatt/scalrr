var QVis = {}; // namespace

//Graph object constructor
QVis.Graph = function(rootid,opts) {
	opts = opts || {};
	console.log(['Graph opts', opts, opts.r||1.5])
	this.rootid = rootid;
	this.overlap = opts.overlap || -2;

	this.jsvg = null;
	this.jlegend = null;
	this.xlabeldiv = null;
	this.ylabeldiv = null;
	this.svg = null;

	this.h = opts['h'] || 300;
	this.w = opts['w'] || 800;
	this.px = 40;
	this.py = 30;
}

//error reporting function
QVis.Graph.prototype.error = function(msg) {
	div = $("<div/>").attr({'class':"alert alert-error"})
	a = $("<a/>").addClass('close').attr('data-dismiss', 'alert').text('x')
	div.append(a).text(msg);
	$("#messagebox").append(div);
}

//option updating function
QVis.Graph.prototype.update_opts = function (opts) {
	if (!opts) return;
	this.overlap = opts['overlap'] || this.overlap || -2;
	this.r = opts['r'] || this.r || 1.5;
	this.h = opts['h'] || this.h || 300;
	this.w = opts['w'] || this.w || 800;		
}

//data wrapper function
QVis.Graph.prototype.get_data_obj = function(d,type){
	if(type === 'int32' || type === 'int64' || type === 'double') {
		return d;
	} else if(type === 'datetime') {
		return new Date(d*1000);
	} else { // default
		return d;
	}
}

//dupe remover (for primatives and strings only) function
QVis.Graph.prototype.remove_dupes = function(arr) {
	var i,
		len=arr.length,
		out=[],
		obj={};

	for (i=0;i<len;i++) {
		obj[arr[i]]=0;
	}
	for (i in obj) {
		out.push(i);
	}
	return out;
}

//TODO: fix this. it's ugly
QVis.Graph.prototype.createScale = function(_data,_types,label,axislength,axispadding,invert) {
	var scale;
	if(_types[label] === 'int32' || _types[label] === 'int64' || _types[label] === 'double') {
		minx = d3.min(_data.map(function(d){return d[label];}));
		maxx = d3.max(_data.map(function(d){return d[label];}));
		console.log("ranges: "+minx+","+maxx);
		if(invert) {
			scale = d3.scale.linear()
				.domain([this.get_data_obj(maxx,_types[label]), this.get_data_obj(minx,_types[label])])
				.range([axispadding,axislength-axispadding]);
		} else {
			scale = d3.scale.linear()
				.domain([this.get_data_obj(minx,_types[label]), this.get_data_obj(maxx,_types[label])])
				.range([axispadding,axislength-axispadding]);
		}
	} else if (_types[label] === "datetime") {
		minx = d3.min(_data.map(function(d){return d[label];}));
		maxx = d3.max(_data.map(function(d){return d[label];}));
		console.log("ranges: "+minx+","+maxx);
		console.log("ranges: "+this.get_data_obj(minx)+","+this.get_data_obj(maxx));
		if(invert) {
			scale = d3.time.scale()
				.domain([this.get_data_obj(maxx,_types[label]), this.get_data_obj(minx,_types[label])])
				.range([axispadding,axislength-axispadding]);
		} else {
			scale = d3.time.scale()
				.domain([this.get_data_obj(minx,_types[label]), this.get_data_obj(maxx,_types[label])])
				.range([axispadding,axislength-axispadding]);
		}
	} else if (_types[label] === 'string') {
		self.strings = []
		_data.map(function(d){self.strings.push(d[label]);});
		self.strings = this.remove_dupes(self.strings);
		scale = d3.scale.ordinal().domain(self.strings);
		var steps = (axislength-2*axispadding)/(self.strings.length-1);
		var range = [];
		if(invert) {
			for(var i = self.strings.length-1; i >= 0 ;i--){
				range.push(axispadding+steps*i);
			}
		} else {
			for(var i = 0; i < self.strings.length;i++){
				range.push(axispadding+steps*i);
			}
		}
		scale.range(range);
	} else {
		console.log("unrecognized type: "+_types[label]);
	}
	return scale;
}

QVis.Graph.prototype.add_axes = function(xscale,yscale,x_label,y_label,stringticks,_types){
	var self = this;
	var xaxis = d3.svg.axis().scale(xscale).orient('bottom').tickPadding(10);// orient just describes what side of the axis to put the text on
	var yaxis = d3.svg.axis().scale(yscale).orient('left').tickPadding(10);
	var df = d3.time.format("%Y-%m-%d");
	if(_types[x_label] === "datetime") {
		xaxis.ticks(d3.time.days,1);
	} else if(_types[x_label] === 'string') {
		
	} else {
		xaxis.ticks(10);
	}
	if(_types[y_label] === "datetime") {
		yaxis.ticks(d3.time.days,1);
	} else if(_types[y_label] === 'string') {
		
	} else {
		yaxis.ticks(6);
	}
	xaxis.tickSize(-this.h+2*this.py); // makes the tick lines
	yaxis.tickSize(-this.w+2*this.px); // makes the tick lines

	if(_types[x_label] === "datetime") {
		xaxis.tickFormat(df);
	}
	if(_types[y_label] === "datetime") {
		yaxis.tickFormat(df);
	}

	this.svg.append("g")
	      .attr("class", "xaxis")
	      .attr("transform", "translate(0," + (this.h-this.py) + ")")
	      .call(xaxis);

	this.svg.append("g")
	      .attr("class", "yaxis")
	      .attr("transform", "translate("+this.px+" 0)")
	      .call(yaxis);
}

QVis.Graph.prototype.drawCircles = function(container,_data,_types,xscale,yscale,x_label,y_label,radius,color) {
	var temp = this;
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
		container.selectAll('circle')
				.data(data)
			.enter().append('circle')
				.attr('cy', function(d) { return yscale(temp.get_data_obj(d[y_label],_types[y_label]))})
				.attr('cx', function(d) { return xscale(temp.get_data_obj(d[x_label],_types[x_label]))})
				.attr('r', function(d) { return radius(temp.get_data_obj(d[x_label],_types[x_label]))})
				.attr('fill', function(d) { return color(temp.get_data_obj(d[x_label],_types[x_label]))})
				.attr('label', x_label);
	}
}

// just spits out a radius of 2
QVis.Graph.prototype.defaultRadius = function(d) {
	return 2;
}

// just spits out blue
QVis.Graph.prototype.defaultColor = function(d) {
	return 'blue';
}

QVis.Graph.prototype.drawRects = function(container,_data,_types,xscale,yscale,x_label,y_label,width,height,color) {
	var temp = this;
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
		container.selectAll('rect')
				.data(data)
			.enter().append('rect')
				.attr('y', function(d) { return yscale(temp.get_data_obj(d[y_label],_types[y_label]))})
				.attr('x', function(d) { return xscale(temp.get_data_obj(d[x_label],_types[x_label]))})
				.attr('width', function(d) { return width(temp.get_data_obj(d[x_label],_types[x_label]))})
				.attr('height', function(d) { return height(temp.get_data_obj(d[x_label],_types[x_label]))})
				.attr('fill', function(d) { return color(temp.get_data_obj(d[x_label],_types[x_label]))})
				.attr('label', x_label);
	}
}

QVis.Graph.prototype.drawLines = function(container,_data,_types,xscale,yscale) {


}
