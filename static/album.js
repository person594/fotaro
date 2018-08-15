var getJSON = function(url, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.responseType = 'json';
    xhr.onload = function() {
        callback(xhr.response);
    };
    xhr.send();
};

function add_img_to_flow(hash) {
    var flow = document.getElementById('flow');
    var img = document.createElement('img');
    img.src = "/photo/" + hash;
    img.onload = reflow;
    flow.append(img);
}

function reflow() {
    var flow = document.getElementById('flow');
    var flow_width = flow.clientWidth - 10;
    var row = []
    var row_width = 0
    var i = 0;
    while (i < flow.childElementCount) {
	child = flow.children[i]
	if (child.tagName == "BR") {
	    child.remove()
	    continue;
	}
	var aspectRatio = child.naturalWidth / child.naturalHeight;
	child.width = child.height * aspectRatio;
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
    }
    ratio = flow_width / row_width;
    if (ratio < 1.25) {
	row.forEach(function(img) {
	    img.width *= ratio;
	});
    }
}

if (document.URL.indexOf("?") < 0) {
    listName = "all"
} else {
    listName = document.URL.split("?")[1]
}

getJSON("/list/" + listName, function(list) {
    list.forEach(function(image) {
	add_img_to_flow(image);
    });
});



