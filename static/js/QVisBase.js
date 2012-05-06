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

	this.h = opts['h'] || 500;
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
QVis.Graph.prototype.createScale = function(_data,_types,label,axislength,axispadding,invert,color) {
	var scale;
	if(_types[label] === 'int32' || _types[label] === 'int64' || _types[label] === 'double') {
		minx = d3.min(_data.map(function(d){return d[label];}));
		maxx = d3.max(_data.map(function(d){return d[label];}));
		console.log("ranges: "+minx+","+maxx);
		if(color){
			scale = d3.scale.quantize();
		} else {
			scale = d3.scale.linear();
		}
		if(invert) {
			scale.domain([this.get_data_obj(maxx,_types[label]), this.get_data_obj(minx,_types[label])])
				.range([axispadding,axislength-axispadding]);
		} else {
			scale.domain([this.get_data_obj(minx,_types[label]), this.get_data_obj(maxx,_types[label])])
				.range([axispadding,axislength-axispadding]);
		}
	} else if (_types[label] === "datetime") {
		minx = d3.min(_data.map(function(d){return d[label];}));
		maxx = d3.max(_data.map(function(d){return d[label];}));
		console.log("ranges: "+minx+","+maxx);
		console.log("true date ranges: "+this.get_data_obj(minx,_types[label])+","+this.get_data_obj(maxx,_types[label]));
		if(color && invert) {
			scale = d3.scale.quantize().domain([maxx,minx])
					.range([axispadding,axislength-axispadding]);
		} else if (color) {
			scale = d3.scale.quantize().domain([minx,maxx])
					.range([axispadding,axislength-axispadding]);
		} else if(invert) {
				scale = d3.time.scale().domain([this.get_data_obj(maxx,_types[label]), this.get_data_obj(minx,_types[label])])
					.range([axispadding,axislength-axispadding]);
		} else {
			console.log("date got here");
			scale = d3.time.scale().domain([this.get_data_obj(minx,_types[label]), this.get_data_obj(maxx,_types[label])])
				.range([axispadding,axislength-axispadding]);
		}
	} else if (_types[label] === 'string') {
		self.strings = []
		_data.map(function(d){self.strings.push(d[label]);});
		self.strings = this.remove_dupes(self.strings);
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
		scale = d3.scale.ordinal().domain(self.strings)
		if(!color) {
			scale.range(range);
		}
	} else {
		console.log("unrecognized type: "+_types[label] + " for "+label);
	}
	return scale;
}
// clear the relevant
QVis.Graph.prototype.clear = function() {
	this.map = $("#"+this.rootid + " #map");
	this.jsvg = $("#"+this.rootid + " svg");
	this.jlegend = $("#"+this.rootid+" .legend");
	this.xlabeldiv = $("#"+this.rootid+" .xlabel");	
	this.ylabeldiv = $("#"+this.rootid+" .ylabel");	
	this.zlabeldiv = $("#"+this.rootid+" .zlabel");	
	this.jsvg.empty(); this.jlegend.empty(); this.xlabeldiv.empty(); this.ylabeldiv.empty(); this.zlabeldiv.empty(); this.map.empty();
	this.map.append('<div></div>');
}

// perform basic rendering tasks common to all graphs
QVis.Graph.prototype.render = function(_data, _labels,_types, opts) {
	// user wants us to draw something, so we know we have data now.
	//assumption: data is always presented with labels
	if (!_labels || typeof(_labels) == 'undefined') {
		QVis.error("Did not get any data to render!")
		return;
	}

	this.update_opts(opts); // if new options are passed, update the options

	//clear everything to get them ready for drawing
	this.clear();

	// you should know why this is necessary
	var self = this;

	//console.log("this.rootid: " + this.rootid+", self.rootid: "+self.rootid);
	//console.log("this == self?" + this === self);

	// _labels.names contains the columns that will be plotted on the y-axis
	// I iterate through each column and consolidate the points that would be rendered
	// This means that there could be overlapping points from two different columns
	var x_label = _labels.x,
		y_label = _labels.y,
		cscale = d3.scale.category10().domain(_labels.names.map(function(d) {return d['name'];}));  // color scale

	var z_label = '';
	if(this.selectz) {
		if(_labels.z === '') {
			for(var i = 0; i < _labels.names.length; i++) {
				if((_types[_labels.names[i]['name']] == 'int32') || (_types[_labels.names[i]['name']] == 'int64') || (_types[_labels.names[i]['name']] == 'double')) {
					z_label = _labels.names[i]['name'];			
					break;
				}
			}
		} else {
			z_label = _labels.z;
		}
	}
	console.log('z_label: '+z_label);
	//TODO: push the legend and menu features into the graph object
	// add the legend and color it appropriately
	var legend = d3.selectAll(this.jlegend.get()).selectAll('text')
			.data(_labels.names)
		.enter().append('span')
			//.style('float', 'left')
			.style('color', function(d) {return cscale(d['name']);})
			.text(function(d) {return d['name'];});
	
	//
	// render x-axis select options
	if(this.selectx) {
		var xaxisselect = this.xlabeldiv.append($("<select></select>")).find("select");
		var xaxislabel = d3.selectAll(xaxisselect.get()).selectAll("option")
				.data(_labels.names)
			.enter().append("option")
				.attr("value", function(d) { return d['name'];})
				.text(function(d) { return d['name'];});
		xaxisselect.val(x_label);
		console.log(_labels.names);

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
				var yval = '';
				if(self.selecty) {
					yval = $("#"+self.rootid+" .ylabel select").val(); // should be the same as before
				}
				var zval = '';
				if(self.selectz) {
					zval = $("#"+self.rootid+" .zlabel select").val(); // should be the same as before
				}
				console.log(["selected option", selectedval, val])				
				if (val == selectedval) return;
				selectedval = val;
				var newlabels = {"x" : val,"y": yval, "z":zval, "names" : _labels.names,'dimnames':_labels.dimnames,'dimwidths':_labels.dimwidths,'dimbases':_labels.dimbases};

				self.render(_data, newlabels,_types, opts);
			});
		})();
	}

	//
	// render y-axis select options
	if(this.selecty) {
		var yaxisselect = this.ylabeldiv.append($("<select></select>")).find("select");
		var yaxisattrselect = yaxisselect.append($('<optgroup label="attrs"></optgroup>')).find("optgroup");
		var yaxislabel = d3.selectAll(yaxisattrselect.get()).selectAll("option")
				.data(_labels.names)
			.enter().append("option")
				.attr("value", function(d) { return d['name'];})
				.text(function(d) { return d['name'];});
		yaxisselect.val(y_label);

		(function() {
			var selectedval = y_label;
			$("#"+self.rootid+" .ylabel select").change(function() {
				var val = $("#"+self.rootid+" .ylabel select").val();
				var xval;
				if(self.selectx) {
					xval = $("#"+self.rootid+" .xlabel select").val(); // should be the same as before
				}
				var zval = '';
				if(self.selectz) {
					zval = $("#"+self.rootid+" .zlabel select").val(); // should be the same as before
				}
				console.log(["selected option", selectedval, val])				
				if (val == selectedval) return;
				selectedval = val;
				var newlabels = {"y" : val,"x": xval, "z":zval, 'names' : _labels.names,'dimnames':_labels.dimnames,'dimwidths':_labels.dimwidths,'dimbases':_labels.dimbases};

				self.render(_data, newlabels,_types, opts);
			});
		})();
	}

	//
	// render z-axis select options
	if(this.selectz) {
		var zaxisselect = this.zlabeldiv.append($("<select></select>")).find("select");
		var zaxislabel = d3.selectAll(zaxisselect.get()).selectAll("option")
				.data(_labels.names.filter(function(d){return (_types[d['name']] == 'int32')||(_types[d['name']] == 'int64')||(_types[d['name']] == 'double');}))
			.enter().append("option")
				.attr("value", function(d) { return d['name'];})
				.text(function(d) { return d['name'];});
		zaxisselect.val(z_label);

		//
		// I create and execute this anonymous function so
		// selectedval will be private to and accessible by the .change() callback function
		// Manually set the new labels and call render_scatterplot again
		// 
		// notice that I use "self" instead of "this".
		//
		(function() {
			var selectedval = z_label;
			$("#"+self.rootid+" .zlabel select").change(function() {
				var val = $("#"+self.rootid+" .zlabel select").val();
				var yval = '';
				var xval = '';
				if(self.selecty) {
					yval = $("#"+self.rootid+" .ylabel select").val(); // should be the same as before
				}
				if(self.selectx) {
					xval = $("#"+self.rootid+" .xlabel select").val(); // should be the same as before
				}
				console.log(["selected option", selectedval, val])				
				if (val == selectedval) return;
				selectedval = val;
				var newlabels = {"z" : val,"y": yval, "x":xval, "names" : _labels.names,'dimnames':_labels.dimnames,'dimwidths':_labels.dimwidths,'dimbases':_labels.dimbases};

				self.render(_data, newlabels,_types, opts);
			});
		})();
	}

	return {'x_label':x_label,'y_label':y_label,'z_label':z_label};
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
	/*
	var range = 100;
	var steps = _data.length/range+1;
	for(var drawindex = 0; (drawindex < steps) && (drawindex*range < _data.length); drawindex++) {
		console.log("drawing range: "+drawindex*range+"-"+(drawindex*range+range));
		var data;
		if(drawindex*range+range > _data.length) {
			data = _data.slice(drawindex*range,_data.length)
		} else {
			data = _data.slice(drawindex*range,drawindex*range+range)
		}
		//console.log(data);
		var circles = d3.select("#"+this.rootid + " svg g.circlecontainer").selectAll('circle')
			.data(data,function(d,i){return drawindex*range+i;}) //need to specify an id so points don't get replaced
				
		circles.enter().append('circle')
			.attr('cy', function(d) { return yscale(temp.get_data_obj(d[y_label],_types[y_label]));})
			.attr('cx', function(d) { return xscale(temp.get_data_obj(d[x_label],_types[x_label]));})
			.attr('r', function(d) { return radius(temp.get_data_obj(d[x_label],_types[x_label]));})
			.attr('fill', function(d){if(drawindex === 0){return 'blue';}else{returncolor(d);}})
			.attr('label', function(d,i){return drawindex*range+i;});
	}
	*/

	for(var drawindex = 0; drawindex < _data.length; drawindex++) {
		container.append('circle')
			.attr('cy', yscale(temp.get_data_obj(_data[drawindex][y_label],_types[y_label])))
			.attr('cx', xscale(temp.get_data_obj(_data[drawindex][x_label],_types[x_label])))
			.attr('r', radius(temp.get_data_obj(_data[drawindex][x_label],_types[x_label])))
			.attr('fill', color(_data[drawindex]))
			.attr('label', drawindex);
	}
}

// just spits out a radius of 2
QVis.Graph.prototype.defaultRadius = function(d) {
	return 2;
}

// just spits out blue
QVis.Graph.prototype.defaultColor = function(d) {
	return 'red';
}

QVis.Graph.prototype.drawRects = function(container,_data,_types,xscale,yscale,x_label,y_label,width,height,color) {
	var temp = this;
	/*
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
	*/
	for(var drawindex = 0; drawindex < _data.length; drawindex++) {
		//console.log(xscale(temp.get_data_obj(_data[drawindex][y_label],_types[x_label])));
		//console.log(yscale(temp.get_data_obj(_data[drawindex][y_label],_types[y_label])));
		//console.log(width(temp.get_data_obj(_data[drawindex][x_label],_types[x_label])));
		//console.log(height(temp.get_data_obj(_data[drawindex][x_label],_types[x_label]));
		//console.log(color(_data[drawindex]));
		container.append('rect')
			.attr('y', yscale(temp.get_data_obj(_data[drawindex][y_label],_types[y_label])))
			.attr('x', xscale(temp.get_data_obj(_data[drawindex][x_label],_types[x_label])))
			.attr('width', width(temp.get_data_obj(_data[drawindex][x_label],_types[x_label])))
			.attr('height', height(temp.get_data_obj(_data[drawindex][x_label],_types[x_label])))
			.attr('fill', color(_data[drawindex]))
			.attr('label', drawindex);
	}
}

QVis.Graph.prototype.drawLines = function(container,_data,_types,xscale,yscale) {
	//sort the data
	//draw then draw the lines

}
