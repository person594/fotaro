function add_img_to_flow(hash) {
    var flow = document.getElementById('flow');
    var img = document.createElement('img');
    img.src = "/photo/" + hash;
    img.onload = reflow;
    flow.append(img);
}

function reflow() {
    var flow = document.getElementById('flow');
    var flow_width = flow.clientWidth;
    var row = []
    var row_width = 0
    var i = 0;
    while (i < flow.childElementCount) {
	child = flow.children[i]
	if (child.tagName == "BR") {
	    child.remove()
	    continue;
	}
	var next_width = row_width + child.clientWidth;
	var prev_badness = Math.abs(Math.log(row_width / flow_width));
	var next_badness = Math.abs(Math.log(next_width / flow_width));
	if (next_badness < prev_badness) {
	    row.push(child)
	    row_width = next_width
	    ++i;
	} else {
	    ratio = flow_width / row_width;
	    row.forEach(function(img) {
		img.width *= ratio;
	    });
	    row = [child];
	    row_width = child.clientWidth;
	    flow.insertBefore(document.createElement("br"), child);
	    i += 2;
	}
	ratio = flow_width / row_width;
	if (ratio < 1) {
	    row.forEach(function(img) {
		img.width *= ratio;
	    });
	}
    }
}

add_img_to_flow("362607ab46eb80b2c7961ce76bdc7b440910d59b5e8840ea45512dfd16113a87");
add_img_to_flow("13c3096dc1a50d2061ee96110aa8abaf23266f43deab7e78d6aec71dcc6563f6");
add_img_to_flow("362607ab46eb80b2c7961ce76bdc7b440910d59b5e8840ea45512dfd16113a87");
add_img_to_flow("13c3096dc1a50d2061ee96110aa8abaf23266f43deab7e78d6aec71dcc6563f6");
add_img_to_flow("362607ab46eb80b2c7961ce76bdc7b440910d59b5e8840ea45512dfd16113a87");
add_img_to_flow("13c3096dc1a50d2061ee96110aa8abaf23266f43deab7e78d6aec71dcc6563f6");
add_img_to_flow("362607ab46eb80b2c7961ce76bdc7b440910d59b5e8840ea45512dfd16113a87");
add_img_to_flow("13c3096dc1a50d2061ee96110aa8abaf23266f43deab7e78d6aec71dcc6563f6");
add_img_to_flow("362607ab46eb80b2c7961ce76bdc7b440910d59b5e8840ea45512dfd16113a87");
add_img_to_flow("13c3096dc1a50d2061ee96110aa8abaf23266f43deab7e78d6aec71dcc6563f6");
add_img_to_flow("362607ab46eb80b2c7961ce76bdc7b440910d59b5e8840ea45512dfd16113a87");

