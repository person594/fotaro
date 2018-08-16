chunkSize = 50
photoList = []
rowHeight = 300

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

scrollHookActive = true;

flow = document.getElementById('flow');
modal = document.getElementById("modal")
modalImg = document.getElementById("modalImg")
modalPlaceholderImg = document.getElementById("modalPlaceholderImg")

modalIndex = -1

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


function scrollHook(e) {
    if (!scrollHookActive){
	return
    }
    scrollHookActive = false;
    loadChunk().then(function() {
	scrollHookActive = true;
    });
}

function generatePhotoElements() {
    photoList.forEach(function(l, i) {
	hash = l[0];
	var div = document.createElement("div");
	div.id = "photo" + i
	div.classList.add("photoElement");
	var a = document.createElement("a");
	a.href = "#photo" + i
	a.onclick = function() {
	    modalShow(hash);
	};
	div.append(a);
	var img = document.createElement("img");
	//img.src = "/thumb/" + hash
	a.append(img);
	flow.append(div);
    });
}

function loadPhoto(idx) {
    if (idx < 0 || idx >= photoList.length) {
	return Promise.resolve();
    }
    var hwh = photoList[idx];
    var hash = hwh[0];
    var photoElement = document.getElementById("photo" + idx);
    img = photoElement.children[0].children[0];
    img.src = "/thumb/" + hash;
    return new Promise(function(resolve, reject) {
	img.onload = resolve;
    });
}

function searchForVisiblePhoto() {
    lower = 0;
    upper = photoList.length;
    while (lower < upper) {
	console.log(lower, upper)
	idx = Math.floor((lower + upper) / 2);
	pe = document.getElementById("photo" + idx);
	rect = pe.getBoundingClientRect();
	if (rect.bottom < 0) {
	    lower = idx;
	} else if (rect.top > (window.innerHeight)) {
	    upper = idx;
	} else {
	    return idx;
	}
    }
    return null;
}

function loadChunk() {
    center = searchForVisiblePhoto();
    radius = Math.floor(chunkSize / 2);
    promises = [loadPhoto(center)]
    for (var d = 1; d < radius; ++d) {
	promises.push(loadPhoto(center + d));
	promises.push(loadPhoto(center - d));
    }
    return Promise.all(promises)
}

/*
function loadMorePhotos(n) {
    upper = Math.min(photos.length, nLoaded + n)
    promises = []
    while (nLoaded < upper) {
	promises.push(addPhotoToFlow(photos[nLoaded++]));
    }
    return Promise.all(promises);
}

n_photos_added = 0
function addPhotoToFlow(hash) {
    var div = document.createElement("div");
    div.id = "photo" + n_photos_added
    div.classList.add("photoElement");
    var a = document.createElement("a");
    a.href = "#photo" + n_photos_added
    a.onclick = function() {
	modalShow(hash);
    };
    div.append(a);
    var img = document.createElement("img")
    img.src = "/thumb/" + hash
    a.append(img)
    flow.append(div);
    ++n_photos_added;
    return new Promise(function(resolve, reject) {
	img.onload = resolve;
    }).then(reflow);
}
*/
function reflow() {
    console.log("reflow started")
    var flowWidth = flow.clientWidth - 10;
    photoElements = []
    while (flow.childElementCount > 0) {
	child = flow.children[0]
	if (child.className == 'photoElement') {
	    photoElements.push(child);
	}
	child.remove();
    }
    var row = []
    var rowWidth = 0
    photoList.forEach(function(hwh, i) {
	hash = hwh[0]
	w = hwh[1]
	h = hwh[2]
	photoElement = photoElements[i]
	var aspectRatio = w/h
	img = photoElement.children[0].children[0]
	img.height = rowHeight
	img.width = rowHeight * aspectRatio
	var nextWidth = rowWidth + img.width;
	var prevBadness = Math.abs(Math.log(rowWidth / flowWidth));
	var nextBadness = Math.abs(Math.log(nextWidth / flowWidth));
	if (nextBadness < prevBadness) {
	    row.push(photoElement)
	    rowWidth = nextWidth
	    ++i;
	} else {
	    rowClientWidth = 0
	    row.forEach(function(photoElement) {
		flow.append(photoElement)
		img = photoElement.children[0].children[0]
		img.height = rowHeight;

		rowClientWidth += photoElement.clientWidth
	    });
	    ratio = flowWidth / rowClientWidth
	    row.forEach(function(photoElement) {
		img = photoElement.children[0].children[0]
		img.width *= ratio;
	    });
	    flow.append(document.createElement("br"));
	    row = [photoElement];
	    rowWidth = img.width
	}
    });

    ratio = flowWidth / rowWidth;
    if (ratio < 1.25) {
	row.forEach(function(img) {
	    img.width *= ratio;
	});
    }
    console.log("reflowed " + photoList.length + " photos.")
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

if (document.URL.indexOf("?") < 0) {
    listName = "all"
} else {
    listName = document.URL.split("?")[1]
}

getJSON("/list/" + listName).then(function(list) {
    photoList = list;
    generatePhotoElements();
    reflow();
});


