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

QVis.Graph.prototype.createScale = function(_data,_types,label,axislength,axispadding,invert) {
	var scale;
	if(_types[label] === 'int32' || _types[label] === 'int64' || _types[label] === 'double') {
		minx = d3.min(_data.map(function(d){return d[label];}));
		maxx = d3.max(_data.map(function(d){return d[label];}));
		console.log("ranges: "+minx+","+maxx);
		if(invert) {
			scale = d3.scale.linear().domain([this.get_data_obj(maxx,_types[label]), this.get_data_obj(minx,_types[label])]).range([axispadding,axislength-axispadding]);
		} else {
			scale = d3.scale.linear().domain([this.get_data_obj(minx,_types[label]), this.get_data_obj(maxx,_types[label])]).range([axispadding,axislength-axispadding]);
		}
	} else if (_types[label] === "datetime") {
		minx = d3.min(_data.map(function(d){return d[label];}));
		maxx = d3.max(_data.map(function(d){return d[label];}));
		console.log("ranges: "+minx+","+maxx);
		console.log("ranges: "+this.get_data_obj(minx)+","+this.get_data_obj(maxx));
		if(invert) {
			scale = d3.time.scale().domain([this.get_data_obj(maxx,_types[label]), this.get_data_obj(minx,_types[label])]).range([axispadding,axislength-axispadding]);
		} else {
			scale = d3.time.scale().domain([this.get_data_obj(minx,_types[label]), this.get_data_obj(maxx,_types[label])]).range([axispadding,axislength-axispadding]);
		}
	} else if (_types[label] === 'string') {
		self.strings = []
		_data.map(function(d){self.strings.push(d[label]);});
		self.strings = this.remove_dupes(self.strings);
		scale = d3.scale.ordinal().domain(self.strings);
		var steps = (axislength-2*axispadding)/(self.strings.length-1);
		var range = [];
		if(invert) {
			for(var i = self.strings.length-1; i >= 0 ;i--){range.push(axispadding+steps*i);}
		} else {
			for(var i = 0; i < self.strings.length;i++){range.push(axispadding+steps*i);}
		}
		scale.range(range);
	} else {
		console.log("unrecognized type: "+_types[label]);
	}
	return scale;
}

QVis.Graph.prototype.add_axes = function(xscale,yscale,x_label,y_label,stringticks,_types){
	var self = this;
	var xaxis = d3.svg.axis().scale(xscale).orient('bottom').tickPadding(10);
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
	xaxis.tickSize(-this.h+2*this.py);
	yaxis.tickSize(-this.w+2*this.px);

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
