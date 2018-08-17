chunkSize = 50;
photoList = [];
rows = [];
photoBounds = [];
rowHeight = 300;
scrollTimer = 500;
loadedPhotoElements = {};

var getJSON = function(url, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.responseType = 'json';
    return new Promise(function(resolve, reject) {
	xhr.onload = function() {
	    resolve(xhr.response);
	};
	xhr.send();
    });
};

function wait(timeout) {
    return new Promise(function(resolve, reject) {
	setTimeout(resolve, timeout);
    });
}



flow = document.getElementById('flow');
modal = document.getElementById("modal")
modalImg = document.getElementById("modalImg")
modalPlaceholderImg = document.getElementById("modalPlaceholderImg")

modalIndex = -1

// Modal Functions

function modalShow(hash) {
    modalIndex = photos.indexOf(hash)
    modal.style.display = "block";
    modalPlaceholderImg.style.display = "block";
    modalPlaceholderImg.src = "/thumb/" + hash
    modalImg.style.display = "none";
    modalImg.src = "/photo/" + hash;
    location.hash = "photo" + modalIndex;
    modalImg.onload = function() {
	modalPlaceholderImg.style.display = "none";
	modalImg.style.display = "block";
    }
}

function modalClose() {
    modal.style.display = "none";
}

function modalPrev(){
    if (modal.style.display == "none")
	return
    if (modalIndex >= 1) {
	--modalIndex;
	modalShow(photos[modalIndex])
    }
}

function modalNext(){
    if (modal.style.display == "none")
	return
    if (modalIndex >= 0 && modalIndex < photos.length - 1) {
	++modalIndex;
	modalShow(photos[modalIndex])
    }
}

lastScroll = new Date();
function scrollHook(e) {
    lastScroll = new Date();
    wait(scrollTimer).then(function() {
	if (new Date() - lastScroll > 0.9*scrollTimer) {
	    loadChunk();
	}
    });
}

function loadPhoto(idx) {
    if (idx < 0 || idx >= photoList.length || idx in loadedPhotoElements) {
	return Promise.resolve();
    }
    var hwh = photoList[idx];
    var hash = hwh[0];
    var pe = document.createElement("div");
    pe.id = "photo" + idx;
    pe.classList.add("photoElement");
    var a = document.createElement("a");
    a.href = "#photo" + idx
    a.onclick = function() {
	modalShow(hash);
    };
    pe.append(a);
    var img = document.createElement("img");
    img.src = "/thumb/" + hash
    a.append(img);
    loadedPhotoElements[idx] = pe;
    return new Promise(function(resolve, reject) {
	img.onload = resolve;
    }).then(function() {
	positionPhotoElement(pe)
    });
}

function photosOnScreen() {
    rect = flow.getBoundingClientRect();
    flowHeight = rect.bottom - rect.top;
    lower = -rect.top / flowHeight;
    upper = (window.innerHeight - rect.top) / flowHeight;
    lower = Math.floor(lower * rows.length);
    upper = Math.ceil(upper * rows.length);
    onScreen = []
    for (var r = lower; r <= upper; ++r) {
	if (r < 0 || r >= rows.length) {
	    continue;
	}
	row = rows[r];
	row.forEach(function(hwhi) {
	    onScreen.push(hwhi[3]);
	});
    }
    return onScreen;
}

function loadChunk() {
    onScreen = photosOnScreen();
    onScreen.forEach(function(idx) {
	loadPhoto(idx);
    });
}

function flowRows() {
    console.log("rowflow started");
    var flowWidth = flow.clientWidth;
    rows = [];
    var row = [];
    var rowWidth = 0;
    var y = 0;
    photoList.forEach(function(hwh, i) {
	if (i == 69)  {
	    debugger;
	}
	var hash = hwh[0];
	var w = hwh[1];
	var h = hwh[2];
	var scaledWidth = w * rowHeight / h;
	var nextRowWidth = rowWidth + scaledWidth;
	var prevBadness = Math.abs(Math.log(rowWidth / flowWidth));
	var nextBadness = Math.abs(Math.log(nextRowWidth / flowWidth));
	if (nextBadness > prevBadness) {
	    rows.push(row);
	    widthScale = flowWidth / rowWidth;
	    var x = 0;
	    row.forEach(function(hwhi) {
		var w = hwhi[1];
		var h = hwhi[2];
		var scaledWidth = widthScale * w * rowHeight / h
		photoBounds.push([x, y, scaledWidth, rowHeight])
		x += scaledWidth;
	    });
	    y += rowHeight;
	    row = [hwh.concat([i])];
	    rowWidth = scaledWidth;
	} else {
	    row.push(hwh.concat([i]))
	    rowWidth = nextRowWidth;
	}
    });
    rows.push(row);
    x = 0;
    row.forEach(function(hwhi) {
	w = hwhi[1];
	h = hwhi[2];
	scaledWidth = w * rowHeight / h
	photoBounds.push([x, y, scaledWidth, rowHeight])
	x += scaledWidth;
    });

    console.log("rowflow done");
}

function reflow() {
    console.log("reflow started")
    flowRows();
    // Remove everything from the flow
    while (flow.hasChildNodes()) {
	flow.removeChild(flow.lastChild);
    }
    // resize the flow
    flow.style.height = rowHeight * rows.length;
    console.log("reflowed " + photoList.length + " photos.")
    for (var idx in loadedPhotoElements) {
	pe = loadedPhotoElements[idx];
	positionPhotoElement(pe);
    }
}

function positionPhotoElement(pe) {
    pe.remove();
    flow.append(pe);
    idx = Number(pe.id.substring(5))
    bounds = photoBounds[idx]
    pe.style.left = bounds[0];
    pe.style.top = bounds[1];
    pe.style.width = bounds[2];
    pe.style.height = bounds[3];
}

document.onkeyup = function(e) {
    var key = e.keyCode ? e.keyCode : e.which;
    switch(key) {
    case 27: // esc
	modalClose();
	break;
    case 37: // left
	modalPrev();
	break
    case 39: // right
	modalNext();
	break;
    } 
}

//document.body.onscroll = scrollHook;

if (document.URL.indexOf("?") < 0) {
    listName = "all"
} else {
    listName = document.URL.split("?")[1]
}

document.body.onscroll = scrollHook;

getJSON("/list/" + listName).then(function(list) {
    photoList = list;
    reflow();
    loadChunk();
});


