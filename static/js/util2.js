function error(msg) {
	div = $("<div/>").attr({'class':"alert alert-error"})
	a = $("<a/>").addClass('close').attr('data-dismiss', 'alert').text('x')
	div.append(a).text(msg);
	$("#messagebox").append(div);
}

// this is like an object
// new render_scatterplot( ... ) to create a new object
// TODO: make this code multiplex based on data types
function render_scatterplot(rootid, opts) {
	opts = opts || {};
	console.log(['render_scatterplot opts', opts, opts.r||1.5])
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

	//unique to scatterplots
	this.circlecontainer = null;
	this.r = opts.r || 1.5;

	// set variables for the functions
	this.update_opts = update_opts;
	this.add_axes = add_axes;
	this.render_scatterplot = _render_scatterplot;
	this.get_data_obj = get_data_obj;
	this.remove_dupes = remove_dupes;

	// I don't really use this right now
	// TODO: make this useful
	function update_opts(opts) {
		if (!opts) return;
		this.overlap = opts['overlap'] || this.overlap || -2;
		this.r = opts['r'] || this.r || 1.5;
		this.h = opts['h'] || this.h || 300;
		this.w = opts['w'] || this.w || 800;		
	}
	
	function get_data_obj(d,type){
		if(type === 'int32' || type === 'int64' || type === 'double') {
			return d;
		} else if(type === 'datetime') {
			return new Date(d*1000);
		} else { // default
			return d;
		}
	}

	function remove_dupes(arr) {
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

	
	// render the x and y axes in svg
	//TODO: make this scale for more/different scales and graphs
	//TODO: make some sort of interface or abstract class that the graph types implement
	function add_axes(xscale, yscale, x_label,y_label,stringticks , _types) {
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

	// main rendering method
	//
	// arguments:
	// _data = [ {colname : val, ...}, ... ]
	// _labels = {
	//    gbs: []   // group by column names.  (options for x-axis)
	//    x: name 	// initial x-axis name
	//	  aggs: []  // column names of aggregates (options for y-axis)
	// 	  id: 'id'  // name of id column
	//	}
	function _render_scatterplot(_data, _labels,_types, opts) {
		//assumption: data is always presented with labels
		if (!_labels || typeof(_labels) == 'undefined') {
			error("Did not get any data to render!")
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
		//
		var labels = _labels.aggs, 
			x_label = _labels.x,
			y_label = _labels.y,
			cscale = d3.scale.category10().domain(labels);  // color scale

		// create x,y axis scales
		var xscale,yscale;
		// THIS IS ONLY IN THE CONTEXT OF SCATTERPLOTS!!! MANY ASSUMPTIONS MADE ABOUT THE DATA HERE
		if(_types[x_label] === 'int32' || _types[x_label] === 'int64' || _types[x_label] === 'double') {
			minx = d3.min(_data.map(function(d){return d[x_label];}));
			maxx = d3.max(_data.map(function(d){return d[x_label];}));
			console.log("ranges: "+minx+","+maxx);
			xscale = d3.scale.linear().domain([get_data_obj(minx,_types[x_label]), get_data_obj(maxx,_types[x_label])]).range([this.px,this.w-this.px]);
		} else if (_types[x_label] === "datetime") {
			minx = d3.min(_data.map(function(d){return d[x_label];}));
			maxx = d3.max(_data.map(function(d){return d[x_label];}));
			console.log("ranges: "+minx+","+maxx);
			console.log("ranges: "+get_data_obj(minx)+","+get_data_obj(maxx));
			xscale = d3.time.scale().domain([get_data_obj(minx,_types[x_label]), get_data_obj(maxx,_types[x_label])]).range([this.px,this.w-this.px]);
		} else if (_types[x_label] === 'string') {
			self.strings = []
			_data.map(function(d){self.strings.push(d[x_label]);});
			self.strings = remove_dupes(self.strings);
			xscale = d3.scale.ordinal().domain(self.strings);
			var steps = (this.w-2*this.px)/(self.strings.length-1);
			var range = [];
			for(var i = 0; i < self.strings.length;i++){range.push(this.px+steps*i);}
			xscale.range(range);
		} else {
			console.log("unrecognized type: "+_types[x_label]);
			console.log("labels: "+x_label+","+y_label);
		}

		if(_types[y_label] === 'int32' || _types[y_label] === 'int64' || _types[y_label] === 'double') {
			miny = d3.min(_data.map(function(d){return d[y_label];}));
			maxy = d3.max(_data.map(function(d){return d[y_label];}));
			console.log("ranges: "+miny+","+maxy);
			yscale = d3.scale.linear().domain([miny,maxy]).range([this.h-this.py, this.py]);
		}
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

				self.render_scatterplot(_data, newlabels,_types, opts);
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

				self.render_scatterplot(_data, newlabels,_types, opts);
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
			.attr("y", this.h-this.py);

		
		//
		// This code renders the actual points
		function add_circle () {
			//console.log("label: "+label);
			//console.log(_data[0]);
			//console.log(_data.length);
			// create the container
			var cellcont = self.circlecontainer.append('g')
					.attr("id", self.rootid+"_cells")
					.attr("x", 0)
					.attr("y", self.h-self.py)
					.attr("width", self.w-2*self.px)					
					.attr("height",  self.h-2*self.py)

			cellcont.attr('class', "circleplot");


			cellcont.selectAll('circle')
					.data(_data)
				.enter().append('circle')
					.attr('cy', function(d) { return yscale(get_data_obj(d[y_label],_types[y_label]))})
					.attr('cx', function(d) {return xscale(get_data_obj(d[x_label],_types[x_label]))})
					.attr('r', 2)
					.attr('fill', 'red')
					.attr('label', x_label).append('text').text(function(d){return x_label+": " + get_data_obj(d[x_label],_types[x_label]) +", "+y_label+": "+get_data_obj(d[y_label],_types[y_label])});
		}
		add_circle();

	}
}

