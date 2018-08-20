chunkSize = 50;
photoList = [];
rows = [];
photoBounds = [];
rowHeight = 300;
scrollTimer = 500;
reflowTimer = 125;
loadedPhotoElements = {};
// load all photos one screen-height above the viewport
loadAbove = 1;
// and three screen-heights below
loadBelow = 3;

selectedPhotos = [];
screenCenterPhoto = 0;

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

//https://stackoverflow.com/questions/133925/javascript-post-request-like-a-form-submit
function post(path, params, method) {
    method = method || "post"; 

    var form = document.createElement("form");
    form.setAttribute("method", method);
    form.setAttribute("action", path);

    for(var key in params) {
        if(params.hasOwnProperty(key)) {
            var hiddenField = document.createElement("input");
            hiddenField.setAttribute("type", "hidden");
            hiddenField.setAttribute("name", key);
            hiddenField.setAttribute("value", params[key]);

            form.appendChild(hiddenField);
        }
    }

    document.body.appendChild(form);
    form.submit();
    form.remove()
}

flow = document.getElementById('flow');
modal = document.getElementById("modal")
modalImg = document.getElementById("modalImg")
modalPlaceholderImg = document.getElementById("modalPlaceholderImg")
modalCloseButton = document.getElementById("modalClose");

sidebarButtonView = document.getElementById("sidebarButtonView");
sidebarButtonSelect = document.getElementById("sidebarButtonSelect");
sidebarButtonDeelect = document.getElementById("sidebarButtonDeelect");
sidebarButtonDownload = document.getElementById("sidebarButtonDownload");
sidebarButtons = {
    "view": sidebarButtonView,
    "select": sidebarButtonSelect,
    "download": sidebarButtonDownload
};

modalIndex = -1

// Modal Functions

function modalShow(idx) {
    modalIndex = idx;
    var hash = photoList[idx][0];
    modal.style.display = "block";
    modalPlaceholderImg.src = "/thumb/" + hash
    modalImg.style.opacity = 0;
    modalImg.src = "/photo/" + hash;
    window.location.hash = idx;
    modalCloseButton.parentElement.href = "#" + idx;
    modalImg.onload = function() {
	modalImg.style.opacity = 1;
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
	modalShow(modalIndex)
    }
}

function modalNext(){
    if (modal.style.display == "none")
	return
    if (modalIndex >= 0 && modalIndex < photoList.length - 1) {
	++modalIndex;
	modalShow(modalIndex)
    }
}

lastScroll = new Date();
function scrollHook(e) {
    updateScreenCenterPhoto();
    lastScroll = new Date();
    wait(scrollTimer).then(function() {
	if (new Date() - lastScroll >= scrollTimer) {
	    loadChunk();
	}
    });
}

function scrollToPhoto(idx) {
    bounds = photoBounds[idx];
    imgCenterY = bounds[1] + 0.5*bounds[3] + flow.offsetTop;
    window.scrollTo(0, imgCenterY - window.innerHeight/2);
}

function hashChangeHook() {
    idx = Number(window.location.hash.substring(1));
    if (idx == idx) {
	scrollToPhoto(idx);
    }
}

function photoClickHook(idx) {
    switch (currentMode) {
    case "view":
	modalShow(idx);
	break;
    case "select":
	togglePhotoSelection(idx);
	break;
    case "download":
	downloadPhoto(idx);
	break;
    }
}

greyOutNonSelectedRule = "div.photoElement{filter: grayscale(75%) contrast(50%);}"

function selectPhoto(idx) {
    deselectPhoto(idx);
    if (selectedPhotos.length == 0) {
	document.styleSheets[0].insertRule(greyOutNonSelectedRule, 0);
    }
    pe = loadedPhotoElements[idx];
    pe.classList.add("photoElementSelected");
    selectedPhotos.push(idx);
    sidebarButtonDeselect.classList.remove('sidebarButtonHidden')
}

function deselectPhoto(idx) {
    pe = loadedPhotoElements[idx];
    pe.classList.remove("photoElementSelected");
    i = selectedPhotos.indexOf(idx);
    if (i >= 0) {
	selectedPhotos.splice(i, 1);
	if (selectedPhotos.length == 0) {
	    sidebarButtonDeselect.classList.add('sidebarButtonHidden');
	    document.styleSheets[0].deleteRule(0);
	}
    }
}

function deselectAllPhotos() {
    while (selectedPhotos.length > 0) {
	deselectPhoto(selectedPhotos[0]);
    }
}

function togglePhotoSelection(idx) {
    pe = loadedPhotoElements[idx];
    if (pe.classList.contains("photoElementSelected")) {
	deselectPhoto(idx);
    } else {
	selectPhoto(idx);
    }
}

function downloadPhotos(indices) {
    if (indices.length == 1) {
	return downloadPhoto(indices[0]);
    }
    hashes = []
    indices.forEach(function(idx) {
	hashes.push(photoList[idx][0]);
    });
    post("/download.tar.gz", {"hashes": hashes.join(",")});
}

function downloadPhoto(idx) {
    var hwh = photoList[idx];
    var hash = hwh[0];
    a = document.createElement("a");
    a.href = "/download/" + hash;
    a.click();
    a.remove();
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
    a.onclick = function() {
	photoClickHook(idx);
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

function updateScreenCenterPhoto() {
    rect = flow.getBoundingClientRect();
    flowHeight = rect.bottom - rect.top;
    if (flowHeight == 0) {
	screenCenterPhoto = 0;
    } else{
	center = (window.innerHeight / 2 - rect.top) / flowHeight;
	centerRow = rows[Math.floor(center * rows.length)]
	i = Math.floor(centerRow.length / 2)
	screenCenterPhoto = centerRow[i][3];
    }
    //el = document.getElementById("photo" + screenCenterPhoto);
    //el.classList.add("photoElementSelected");
}

function photosNearScreen() {
    rect = flow.getBoundingClientRect();
    flowHeight = rect.bottom - rect.top;
    lower = -rect.top / flowHeight;
    upper = (window.innerHeight - rect.top) / flowHeight;
    lower = Math.floor(lower * rows.length);
    upper = Math.ceil(upper * rows.length);
    nRows = upper - lower;
    lower -= loadAbove * nRows;
    upper += loadBelow * nRows;
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
    onScreen = photosNearScreen();
    onScreen.forEach(function(idx) {
	loadPhoto(idx);
    });
}

function flowRows() {
    console.log("rowflow started");
    var flowWidth = flow.clientWidth;
    rows = [];
    photoBounds = [];
    var row = [];
    var rowWidth = 0;
    var y = 0;
    photoList.forEach(function(hwh, i) {
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

currentMode = ""
function setMode(newMode) {
    if (newMode == currentMode) {
	return;
    }
    for (var mode in sidebarButtons) {
	button = sidebarButtons[mode];
	button.classList.remove("sidebarButtonSelected");
    }
    sidebarButtons[newMode].classList.add("sidebarButtonSelected");

    currentMode = newMode;
}

function sidebarButtonHook(button) {
    switch(button) {
    case sidebarButtonView:
	setMode("view");
	break;
    case sidebarButtonSelect:
	setMode("select");
	break;
    case sidebarButtonDeselect:
	deselectAllPhotos();
	break;
    case sidebarButtonDownload:
	if (selectedPhotos.length == 0) {
	    setMode("download");
	    break;
	} else {
	    downloadPhotos(selectedPhotos);
	    deselectAllPhotos();
	}
    }
}

setMode("view");

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

lastResize = new Date();
centerAfterResize = 0
window.onresize = function() {
    lastResize = new Date();
    centerAfterResize = screenCenterPhoto
    wait(reflowTimer).then(function() {
	if (new Date() - lastResize >= reflowTimer) {
	    reflow();
	    scrollToPhoto(centerAfterResize);
	}
    });;
}

if (document.URL.indexOf("?") < 0) {
    listName = "all"
} else {
    listName = document.URL.split("?")[1]
}

document.body.onscroll = scrollHook;
document.body.onhashchange = hashChangeHook;

getJSON("/list/" + listName).then(function(list) {
    photoList = list;
    reflow();
    loadChunk();
});


