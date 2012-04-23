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

// function to render the x and y axes in svg
//TODO: make this scale for more/different scales and graphs
//TODO: make some sort of interface or abstract class that the graph types implement
QVis.Graph.prototype.add_axes = function(xscale, yscale, x_label,y_label,stringticks , _types) {
	//xscale = d3.scale.linear().domain(xscale.domain()).range([this.px, this.w-this.px]);
	//yscale = d3.scale.linear().domain(yscale.domain()).range([this.h-this.py, this.py]);
	var self = this;
	var xticks;
	if(_types[x_label] === "datetime") {
		var df = d3.time.format("%Y-%m-%d");
		xticks = xscale.ticks(d3.time.days,1);
	} else if(_types[x_label] === 'string') {
		xticks = stringticks;
	} else {
		xticks = xscale.ticks(10);
	}
	console.log(xticks);
	var xrules = this.svg.append('g').selectAll('.xlabel')
			.data(xticks)
		.enter().append('g')
			.attr('class', 'xlabel')
			.attr('transform', function(d) {return 'translate('+xscale(d)+' 0)'});
	if(_types[x_label] === "datetime") {
		xrules.append('text')
				.attr('y', this.h)
				.text(function(d) {return df(d);})	
	} else {
		xrules.append('text')
				.attr('y', this.h)
				.text(String)	
	}
	xrules.append('line')
			.attr('y1', this.h-this.py)
			.attr('y2', this.py)
			.attr('stroke', '#ccc');

	var yrules = this.svg.append('g').selectAll('.ylabel')
			.data(yscale.ticks(6))
		.enter().append('g')
			.attr('class', 'ylabel')
			.attr('transform', function(d) {return 'translate(0 '+yscale(d)+')'})
	yrules.append('text')
			.attr('x', 0)
			.text(String);
	yrules.append('line')
			.attr('x1', this.px)
			.attr('x2', this.w-this.px)
			.attr('stroke', '#ccc');		
}
