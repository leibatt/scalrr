function error(msg) {
	div = $("<div/>").attr({'class':"alert alert-error"})
	a = $("<a/>").addClass('close').attr('data-dismiss', 'alert').text('x')
	div.append(a).text(msg);
	$("#messagebox").append(div);
}

// this is like an object
// new render_scatter( ... ) to create a new object
function render_scatter(rootid, brushevent, opts) {

	opts = opts || {};
	console.log(['render_scatter opts', opts, opts.r||1.5])
	this.rootid = rootid;
	this.brushevent = brushevent;
	this.overlap = opts.overlap || -2;
	this.r = opts.r || 1.5;
	this.h = opts['h'] || 300;
	this.w = opts['w'] || 800;
	this.px = 40;
	this.py = 30;
	this.sx = (this.w-(2*this.px)) / this.w;
	this.sy = (this.h-(2*this.py)) / this.h;
	this.jsvg = null;
	this.jlegend = null;
	this.xlabeldiv = null;
	this.svg = null;
	this.circlecontainer = null;
	this.minx = this.maxx = this.miny = this.maxy = null;

	this.update_opts = update_opts;
	this.update_bounds = update_bounds;
	this.add_axes = add_axes;
	this.render_scatter = _render_scatter;
	this.summarize_scatter = summarize_scatter;

	function summarize_scatter(data, labels, color) {
		var h = this.h,
			w = this.w,
			r = this.r*2,
			overlap = this.overlap,
			// I think this is saying, find min and max, using a function that maps the the values to
			// compare by. labels just says what labels are available per data item d
			minx = d3.min(data.map(function(d){return d[labels.x];})),
			maxx = d3.max(data.map(function(d){return d[labels.x];})),
			miny = d3.min(data.map(function(d){return d[labels.y];})),
			maxy = d3.max(data.map(function(d){return d[labels.y];})),
			maxptsx = w / Math.max(r-overlap, 1), // maximum number of points along x axis
			maxptsy = h / Math.max(r-overlap, 1), // maximum number of points along y axis
			// this code breaks up the space in the canvas into maxptsx*maxptsy "bins",
			// each with dimensions dx by dy
			dx = Math.max((maxx - minx) / maxptsx, 1),
			dy = Math.max((maxy - miny) / maxptsy, 1);
		
		//
		// group the points first along x-axis, then on y-axis
		// I recommend understanding how nest works.  
		var data_gb = d3.nest() // key asks for a function that takes a data element d and returns what bin it belongs to
			.key(function(d) {	return Math.floor(d[labels.x] / dx) * dx;	}) // x-bucket
			.key(function(d) {	return Math.floor(d[labels.y] / dy) * dy;	}) // y-bucket
			.entries(data); // entries moves items to their respective locations in the hierarchy, respecting levels of registered keys
					// so in this case, entries will return an array of x bins, and each of these bins points to a set of relevant y bins


		// maximum and minumum number of points that are consolidated together
		var minpts = null, maxpts = null;

		//
		// remember how many values there are
		// 
		// Each consolidated point also keeps track of
		// the x bucket, y bucket, and column name of the point
		// they are used in the main rendering code
		data_gb.forEach(function( xgroup ) {
			xgroup.values.forEach( function( ygroup ) {
				var nvals = ygroup.values.length;	
				ygroup['__label__'] = labels.y;
				ygroup['__x__'] = Number(xgroup.key);
				ygroup['__y__'] = Number(ygroup.key);
				minpts = (minpts == null || minpts > nvals)? nvals : minpts;
				maxpts = (maxpts == null || maxpts < nvals)? nvals : maxpts;
			})
		});
		minpts = (minpts == null)? 0 : minpts;
		maxpts = (maxpts == null)? 1 : maxpts;

                // this stuff is all pretty awful.  It shouldn't be here and is honestly not used
                var mincolor = d3.rgb(color).brighter().hsl(),
                        maxcolor = d3.hsl(color);
                maxcolor.s = 1;
                mincolor.s = 0.2;
                var cscale = d3.scale.linear().range([mincolor.toString(), maxcolor.toString()]).domain([minpts, maxpts]);
                cscale = function(d,i) {return color;};


		// rscale is to scale the radius of the circle by the number of points in the consolidated point
		var rscale = d3.scale.linear().range([this.r, this.r+2.5]).domain([minpts, maxpts]);

		// Summary of values used to aggregate the points
		// n means min, m means max
		var bounds = {	'nx': Math.floor(minx/dx)*dx,
						'mx': Math.floor(maxx/dx)*dx,
						'ny': Math.floor(miny/dy)*dy,
						'my': Math.floor(maxy/dy)*dy,
						'dx': dx,
						'dy': dy };

		return {'data' : data_gb, 'cscale' : cscale, 'bounds' : bounds, 'rscale' : rscale}
	}	

	function update_opts(opts) {
		if (!opts) return;
		this.overlap = opts['overlap'] || this.overlap || -2;
		this.r = opts['r'] || this.r || 1.5;
		this.h = opts['h'] || this.h || 300;
		this.w = opts['w'] || this.w || 800;		
	}

	// n = min, m = max.  nx = min x
	function update_bounds(nx, mx, ny, my) {
		if (this.maxx == null || mx > this.maxx || this.maxx - mx > 0.6 * (this.maxx-this.minx)) 
			this.maxx = mx;
		if (this.maxy == null || my > this.maxy || this.maxy - my > 0.6 * (this.maxy-this.miny)) 
			this.maxy = my;
		if (this.minx == null || nx < this.minx || nx - this.minx > 0.6 * (mx-this.minx)) 
			this.minx = nx;
		if (this.miny == null || ny < this.miny || ny - this.miny > 0.6	 * (my-this.miny)) 
			this.miny = ny;
		console.log(['bounds',[nx, mx, ny, my], 
					 [this.minx, this.maxx, this.miny, this.maxy]]);		

	}
	
	
	// render the x and y axes in svg
	function add_axes(xscale, yscale, ylabels) {
		xscale = d3.scale.linear().domain(xscale.domain()).range([this.px, this.w-this.px]);
		yscale = d3.scale.linear().domain(yscale.domain()).range([this.h-this.py, this.py]);
		var xrules = this.svg.append('g').selectAll('.xlabel')
				.data(xscale.ticks(10))
			.enter().append('g')
				.attr('class', 'xlabel')
				.attr('transform', function(d) {return 'translate('+xscale(d)+' 0)'})
		xrules.append('text')
				.attr('y', this.h)
				.text(String)	
		this.svg.append('line')

		var yrules = this.svg.append('g').selectAll('.ylabel')
				.data(yscale.ticks(6))
			.enter().append('g')
				.attr('class', 'ylabel')
				.attr('transform', function(d) {return 'translate(0 '+yscale(d)+')'})
		yrules.append('text')
				.attr('x', 0)
				.text(String);
		yrules.append('line')
				.attr('x1', this.py)
				.attr('x2', this.w)
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
	function _render_scatter(_data, _labels, opts) {
		if (!_labels || typeof(_labels) == 'undefined') {
			error("Did not get any data to render!")
			return;
		}

		this.update_opts(opts);
		this.jsvg = $("#"+this.rootid + " svg"),
		this.jlegend = $("#"+this.rootid+" .legend");
		this.xlabeldiv = $("#"+this.rootid+" .xlabel");		
		this.jsvg.empty(); this.jlegend.empty(); this.xlabeldiv.empty();

		// you should know why this is necessary
		var self = this; 	

		console.log("this.rootid: " + this.rootid+", self.rootid: "+self.rootid);
		console.log("this == self?" + this === self);
		// _labels.aggs contains the columns that will be plotted on the y-axis
		// I iterate through each column and consolidate the points that would be rendered
		// This means that there could be overlapping points from two different columns
		//
		var labels = _labels.aggs, 
			x_label = _labels.x,
			cscale = d3.scale.category10().domain(labels),  // color scale
			nx = mx = ny = my = null,
			summaries = labels.map(function(label) {
				summary = self.summarize_scatter(_data, {'x':x_label, 'y':label}, cscale(label));
				nx = (nx == null || nx > summary.bounds.nx)? summary.bounds.nx : nx;
				mx = (mx == null || mx < summary.bounds.mx)? summary.bounds.mx : mx;
				ny = (ny == null || ny > summary.bounds.ny)? summary.bounds.ny : ny;
				my = (my == null || my < summary.bounds.my)? summary.bounds.my : my;
				return summary;
			});


		this.update_bounds(nx, mx, ny, my);

		// compute x and y axis domain padding
		var	ysc = ((1-((this.h-(this.py*2) - 5) / (this.h-(this.py*2)))) / 2.0) * (this.maxy - this.miny),
			xsc = ((1-((this.w-(this.px*3) - 10) / (this.w-(this.px*3)))) / 2.0) * (this.maxx - this.minx),
			ysc = isNaN(ysc)? 10 : ysc,
			xsc = isNaN(xsc)? 10 : xsc;
		
		// create x,y axis scales
		var yscale = d3.scale.linear().domain([this.miny - ysc, this.maxy + ysc]).range([this.h-this.py, this.py]),
			xscale = d3.scale.linear().domain([this.minx - xsc, this.maxx + xsc]).range([this.px, this.w-this.px]);

		// this is a hack so that the container containing the points for each y-axis column is
		// 1) scaled down a little bit
		// 2) are positioned and sized the same
		// I realize this is sort of redundant to the code immediately above.
		var ex = [xscale(this.minx*(1-xsc)), xscale(this.maxx*(1+xsc))],
			ey = [yscale(this.miny*(1-ysc)), yscale(this.maxy*(1+ysc))];
		console.log(["scaling", ysc, xsc])



		// add the legend and color it appropriately
		var legend = d3.selectAll(this.jlegend.get()).selectAll('text')
				.data(labels)
			.enter().append('div')
				.style('float', 'left')
				.style('color', cscale)
				.text(String);		
		
		//
		// render x-axis select options
		//
		var xaxisselect = this.xlabeldiv.append($("<select></select")).find("select");
		var xaxislabel = d3.selectAll(xaxisselect.get()).selectAll("option")
				.data(_labels.gbs)
			.enter().append("option")
				.attr("value", String)
				.text(String);
		xaxisselect.val(x_label);
		//
		// I create and execute this anonymous function so
		// selectedval will be private to and accessible by the .change() callback function
		// Manually set the new labels and call render_scatter again
		// 
		// notice that I use "self" instead of "this".
		//
		(function() {
			var selectedval = x_label;
			$("#"+self.rootid+" .xlabel select").change(function() {
				var val = $("#"+self.rootid+" .xlabel select").val();
				console.log(["selected option", selectedval, val])				
				if (val == selectedval) return;
				selectedval = val;
				var newlabels = {"x" : val, "gbs" : _labels.gbs, "aggs" : _labels.aggs};

				self.render_scatter(_data, newlabels, opts);
			});
		})();

		this.svg = d3.selectAll(this.jsvg.get())
			.attr('width', this.w)
			.attr('height', this.h)
			.attr('class', 'g')
			.attr('id', 'svg_'+this.rootid);
		this.add_axes(xscale, yscale, _labels.gbs);
					
		this.circlecontainer = this.svg.append('g')
			.attr("class", "circlecontainer")
			.attr('width', ex[1]-ex[0])
			.attr('height', ey[0]-ey[1])
			.attr("x", ex[0])
			.attr("y", ey[1]);

		
		//
		// This code renders the actual points
		// The key point to note is that I create a new container (cellcont)
		// for each column of data
		//
		function add_circle (summary, idx) {
			var label = labels[idx];
			var color = cscale(label);

			// create the container
			var cellcont = self.circlecontainer.append('g')
					.attr("id", self.rootid+"_cells_"+idx)
					.attr("x", ex[0])
					.attr("y", ey[1])
					.attr("width", ex[1] - ex[0])					
					.attr("height",  Math.abs(ey[1] - ey[0]))
					.attr('class', "circleplot");

			// Remember how the summarize function created two nestings when calling
			// data.nest().key(...).key(...)?
			//
			// This will create a 'g' container for each group of consolidated points with
			// the same x axis bucket
			//
			// I strongly recommend understanding how nest() works and why the code below works
			//
			var cells = cellcont.selectAll('g')
					.data(summary.data)
				.enter().append('g')
			//
			// This draws the y-axis points in each x-axis bucket
			//
			cells.selectAll('circle')
					.data(function(d) { return d.values;})
				.enter().append('circle')
					.attr('cy', function(d) { return yscale(d.key)})
					.attr('cx', function(d) { return xscale(d['__x__'])})
					.attr('r', function(d){return summary.rscale(d.values.length)})
					.attr('fill', function(d) { d['__color__'] = summary.cscale(d.values.length); return d.__color__; })
					.attr('label', label);
		}
		summaries.forEach(add_circle);

		//
		// Brushes are/were not well documented.  I had to look through the implementation
		// to figure out what its doing.
		//
		// This code will find all of the highlighted consolidated circles for each y-axis column
		// and construct a mapping of 
		//           y-axis column -> list of selected (unconsolidated) individual data points 
		//
		var selectedobjs = {};			
		function brushf() {
			var extents = brush.extent();
			labels.forEach(function(l) {selectedobjs[l] = [];})
			console.log(self.svg.attr('id'));
			self.svg.selectAll('circle')
				.attr('fill', function(d, i) {
					var c = d3.select(this),
							x = c.data()[0]['__x__'],
							y = c.data()[0]['__y__'];
					var selected = extents[0][0] <= x &&
								extents[1][0] >= x &&
								extents[0][1] <= y &&
								extents[1][1] >= y;
					if (selected) {
						var list = selectedobjs[c.attr('label')];
						if (typeof(list) != 'undefined')
							list.push.apply(list, c.data()[0].values);
					}
					return selected ? 'black' : c.data()[0]['__color__'];
			})
			
			// if the user defined a callback, then call it.
			if (self.brushevent !== null && typeof(self.brushevent) != "undefined")
				self.brushevent(selectedobjs, _labels);			
		}



		var brush = d3.svg.brush().on('brush', brushf)
				.x(xscale)  // scales the extent (pixel scale bounding box) of the selected region
				.y(yscale); // to the points' attribute values
		this.svg.append('g')
				.attr('class', 'brush')
				.call(brush);

	}
}

