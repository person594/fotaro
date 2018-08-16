minDistBeforeLoad = 1000
chunkSize = 20
pictures = []
nLoaded = 0

var getJSON = function(url, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.responseType = 'json';
    xhr.onload = function() {
        callback(xhr.response);
    };
    xhr.send();
};

scrollHookActive = true;

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
    var flow = document.getElementById('flow')
    scrollBottom = flow.scrollTop + flow.offsetHeight
    marginToBottom = flow.scrollHeight - scrollBottom
    if (marginToBottom <= minDistBeforeLoad) {
	scrollHookActive = false;
	loadMorePhotos(chunkSize).then(function() {
	    scrollHookActive = true;
	});
    }
    console.log(e);
}

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
    var flow = document.getElementById('flow');
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

function reflow() {
    var flow = document.getElementById('flow');
    var flowWidth = flow.clientWidth - 10;
    var row = []
    var rowWidth = 0
    var i = 0;
    while (i < flow.childElementCount) {
	child = flow.children[i]
	if (child.tagName == "BR") {
	    child.remove()
	    continue;
	}
	img = child.children[0].children[0]
	var aspectRatio = img.naturalWidth / img.naturalHeight;
	img.width = img.height * aspectRatio;
	var nextWidth = rowWidth + img.clientWidth;
	var prevBadness = Math.abs(Math.log(rowWidth / flowWidth));
	var nextBadness = Math.abs(Math.log(nextWidth / flowWidth));
	if (nextBadness < prevBadness) {
	    row.push(img)
	    rowWidth = nextWidth
	    ++i;
	} else {
	    ratio = flowWidth / rowWidth;
	    row.forEach(function(img) {
		img.width *= ratio;
	    });
	    row = [img];
	    rowWidth = img.clientWidth;
	    flow.insertBefore(document.createElement("br"), child);
	    i += 2;
	}
    }
    ratio = flowWidth / rowWidth;
    if (ratio < 1.25) {
	row.forEach(function(img) {
	    img.width *= ratio;
	});
    }
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

getJSON("/list/" + listName, function(list) {
    photos = list
    loadMorePhotos(chunkSize);
});



