chunkSize = 50;
photoList = [];
editable = false;
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

albums = [
];
listName = null;

username = null;

var getJSON = function(url) {
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

function post(path, params, responseType) {
    responseType = responseType || "text"
    var xmlhttp = new XMLHttpRequest();
    xmlhttp.open("POST", path, true)
    xmlhttp.responseType = responseType;
    var prom = new Promise(function(resolve, reject) {
	xmlhttp.onreadystatechange = function() {
	    if (xmlhttp.readyState == 4) {
		if (xmlhttp.status >= 200 && xmlhttp.status < 300) {
		    resolve(xmlhttp.response);
		} else {
		    reject(xmlhttp.response);
		}
	    }
	};
    });
    xmlhttp.send(JSON.stringify(params));
    return prom;
}

function downloadBlob(blob, filename) {
    var a = document.createElement("a");
    document.body.append(a);
    a.style.display = "none";
    url = window.URL.createObjectURL(blob);
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
}

flow = document.getElementById('flow');

promptModalBackground = document.getElementById("promptModalBackground");
promptModal = document.getElementById("promptModal");

loginModalBackground = document.getElementById("loginModalBackground");
loginModal = document.getElementById("loginModal");
loginModalCloseButton = document.getElementById("loginModalClose");
loginModalErrorText = document.getElementById("loginModalErrorText");
loginForm = document.getElementById("loginForm");
loginFormUsername = document.getElementById("loginFormUsername");
loginFormPassword = document.getElementById("loginFormPassword");



viewModalBackground = document.getElementById("viewModalBackground")
viewModalImg = document.getElementById("viewModalImg")
viewModalPlaceholderImg = document.getElementById("viewModalPlaceholderImg")
viewModalCloseButton = document.getElementById("viewModalClose");

sidebarButtonLogin = document.getElementById("sidebarButtonLogin");
sidebarButtonView = document.getElementById("sidebarButtonView");
sidebarButtonSelect = document.getElementById("sidebarButtonSelect");
sidebarButtonDeselect = document.getElementById("sidebarButtonDeselect");
sidebarButtonAdd = document.getElementById("sidebarButtonAdd");
sidebarButtonRemove = document.getElementById("sidebarButtonRemove");
sidebarButtonDownload = document.getElementById("sidebarButtonDownload");
sidebarButtonAlbums = document.getElementById("sidebarButtonAlbums");
modeButtons = {
    "view": sidebarButtonView,
    "select": sidebarButtonSelect,
    "add": sidebarButtonAdd,
    "remove": sidebarButtonRemove,
    "download": sidebarButtonDownload
};

editableOnlyButtons = [
    sidebarButtonRemove
];


function setUsername(un) {
    username = un;
    if (username != null) {
	sidebarButtonLogin.classList.add("sidebarButtonLoggedIn");
	sidebarButtonLogin.parentElement.title = "Logged in as " + username;
    } else {
	sidebarButtonLogin.classList.remove("sidebarButtonLoggedIn");
	sidebarButtonLogin.parentElement.title = "Log in";
    }
}

function promptLogin() {
    loginModalBackground.style.display = "block";
    return new Promise(function(resolve, reject) {
	loginModalCloseButton.onclick = function(){
	    resolve(null)
	};
	loginForm.onsubmit = function() {
	    loginModalErrorText.style.display = "none";
	    var username = loginFormUsername.value;
	    var password = loginFormPassword.value;
	    loginFormPassword.value = '';
	    post("/login", {
		"username": username,
		"password": password
	    }).then(resolve, function(response) {
		loginModalErrorText.innerHTML = response;
		loginModalErrorText.style.display = "block"
	    });
	}
    }).then(function(result) {
	if (result != null) {
	    setUsername(result);
	}
	loginModalBackground.style.display = "none";
	location.reload();
    });
}

function logout() {
    return getJSON("/logout").then(function() {
	setUsername(null);
	location.reload()
    });
}

function prompt(text, options, customText) {
    var modalBackground = promptModalBackground.cloneNode(true);
    var modal = modalBackground.querySelector(".modal")
    var closeButton = modalBackground.querySelector(".modalCloseButton")
    var textDiv = document.createElement("div");
    textDiv.classList.add("promptText")
    textDiv.innerHTML = text;
    modal.append(textDiv);
    document.body.append(modalBackground);
    modalBackground.style.display = "block";
    var oldKeyUpHook = document.onkeyup;
    return new Promise(function(resolve, reject) {
	closeButton.onclick = function() {
	    resolve(null);
	};
	document.onkeyup = function(e) {
	    var key = e.keyCode ? e.keyCode : e.which;
	    if (key == 27) {
		resolve(null);
	    }
	};
	options.forEach(function(option) {
	    if (Array.isArray(option)) {
		var value = option[0];
		var display = option[1];
	    } else {
		var value = option
		var display = option
	    }
	    var onclick = function() {
		resolve(value);
	    };
	    var mi = document.createElement("div")
	    mi.classList.add("promptModalItem");
	    mi.innerHTML = display;
	    mi.onclick = onclick;
	    modal.append(mi);
	});

	if (customText) {
	    var form = document.createElement("form");
	    var textbox = document.createElement("input");
	    textbox.classList.add("promptModalItem");
	    textbox.classList.add("textbox");
	    textbox.placeholder = customText
	    textbox.value = customText
	    form.append(textbox);
	    var textboxClicked = false
	    textbox.onclick = function() {
		if (!textboxClicked) {
		    textbox.value = ""
		    textboxClicked = true;
		}
	    };
	    form.onsubmit = function() {
		resolve(textbox.value);
	    }
	    form.action = "javascript:void(0);";
	    modal.append(form);
	}
    }).then(function(selection) {
	modalBackground.remove();
	document.onkeyup = oldKeyUpHook;
	return selection;
    });
}

function flashPhoto(idx) {
    pe = document.getElementById("photo" + idx);
    pe.style.transition = "0s";
    pe.style.filter = "brightness(200%)"
    wasSelected = pe.classList.contains("photoElementSelected");
    pe.classList.add("photoElementSelected")
    wait(0).then(function() {
	pe.style.transition = ""
	pe.style.filter = ""
	if (!wasSelected) {
	    pe.classList.remove("photoElementSelected");
	}
    });

}


viewModalIndex = -1

// ViewModal Functions

function viewModalShow(idx) {
    viewModalIndex = idx;
    var hash = photoList[idx][0];
    viewModalBackground.style.display = "block";
    viewModalPlaceholderImg.src = "/thumb/" + hash
    viewModalImg.style.opacity = 0;
    viewModalImg.src = "/photo/" + hash;
    window.location.hash = idx;
    viewModalCloseButton.parentElement.href = "#" + idx;
    viewModalImg.onload = function() {
	viewModalImg.style.opacity = 1;
    }
}

function viewModalClose() {
    viewModalBackground.style.display = "none";
}

function viewModalPrev() {
    if (viewModalBackground.style.display == "none")
	return
    if (viewModalIndex >= 1) {
	--viewModalIndex;
	viewModalShow(viewModalIndex)
    }
}

function viewModalNext() {
    if (viewModalBackground.style.display == "none")
	return
    if (viewModalIndex >= 0 && viewModalIndex < photoList.length - 1) {
	++viewModalIndex;
	viewModalShow(viewModalIndex)
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
	viewModalShow(idx);
	break;
    case "select":
	togglePhotoSelection(idx);
	break;
    case "download":
	flashPhoto(idx);
	downloadPhoto(idx);
	break;
    case "add":
	flashPhoto(idx);
	addPhotosToAlbum([idx], addAlbum);
	break;
    case "remove":
	removePhotosFromAlbum([idx]);
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
    post("/download", {"hashes": hashes}, "blob").then(function(blob) {
	downloadBlob(blob, "download.tar.gz");
    });
}

function downloadPhoto(idx) {
    var hwh = photoList[idx];
    var hash = hwh[0];
    a = document.createElement("a");
    a.href = "/download/" + hash;
    a.click();
    a.remove();
}

function addPhotosToAlbum(indices, albumName) {
    var hashes = []
    indices.forEach(function(idx) {
	hashes.push(photoList[idx][0]);
    });
    post("/add", {"album": albumName, "hashes": hashes});
}

function removePhotosFromAlbum(indices) {
    var hashes = []
    indices.forEach(function(idx) {
	hashes.push(photoList[idx][0]);
    });
    post("/remove", {"album": listName, "hashes": hashes}).then(function(){
	var newPhotoList = [];
	var indexMap = []
	var newIndex = 0;
	photoList.forEach(function(photo, i) {
	    // if this photo was not to be removed
	    if (indices.indexOf(i) < 0) {
		newPhotoList.push(photo);
		indexMap.push(newIndex++);
	    } else {
		indexMap.push(-1);
	    }
	});
	var newLoadedPhotoElements = {}
	for (var idx in loadedPhotoElements) {
	    var pe = loadedPhotoElements[idx];
	    var newIdx = indexMap[idx];
	    if (newIdx >= 0) {
		newLoadedPhotoElements[newIdx] = loadedPhotoElements[idx];
		pe.id = "photo" + newIdx;
	    } else {
		pe.remove();
	    }
	}
	photoList = newPhotoList;
	loadedPhotoElements = newLoadedPhotoElements;
	reflow();
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
    a.onclick = function() {
	photoClickHook(Number(pe.id.substring(5)));
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
addAlbum = ""
function setMode(newMode) {
    if (newMode == currentMode) {
	return;
    }
    for (var mode in modeButtons) {
	button = modeButtons[mode];
	button.classList.remove("sidebarButtonSelected");
    }
    modeButtons[newMode].classList.add("sidebarButtonSelected");

    currentMode = newMode;
}

function sidebarButtonHook(button) {
    switch(button) {
    case sidebarButtonLogin:
	if (username == null) {
	    promptLogin();
	} else {
	    prompt("Logged in as " + username, ["Log out"]).then(function(result) {
		if (result == "Log out") {
		    return logout()
		}
	    })
	}
	break;
    case sidebarButtonAlbums:
	prompt("Go to album", [["all", "<i>All photos</i>"]].concat(albums), false).then(function(albumName) {
	    if (albumName) {
		location = "/?" + albumName;
	    }
	});
	break;
    case sidebarButtonView:
	setMode("view");
	break;
    case sidebarButtonSelect:
	setMode("select");
	break;
    case sidebarButtonDeselect:
	deselectAllPhotos();
	break;
    case sidebarButtonAdd:
	prompt("Add to album", albums, "New Album").then(function(albumName) {
	    if (!albumName) {
		return;
	    }
	    if (albums.indexOf(albumName) < 0) {
		albums.push(albumName);
	    }
	    addAlbum = albumName;
	    if (selectedPhotos.length == 0) {
		setMode("add");
	    } else {
		addPhotosToAlbum(selectedPhotos, addAlbum)
		deselectAllPhotos();
	    }
	});
	break;
    case sidebarButtonRemove:
	if (selectedPhotos.length == 0) {
	    setMode("remove");
	} else {
	    var selected = selectedPhotos.slice();
	    deselectAllPhotos();
	    removePhotosFromAlbum(selected)
	}
	break;
    case sidebarButtonDownload:
	if (selectedPhotos.length == 0) {
	    setMode("download");
	    break;
	} else {
	    downloadPhotos(selectedPhotos);
	    deselectAllPhotos();
	}
	break;
    }

    
}

setMode("view");

document.onkeyup = function(e) {
    var key = e.keyCode ? e.keyCode : e.which;
    switch(key) {
    case 27: // esc
	viewModalClose();
	break;
    case 37: // left
	viewModalPrev();
	break
    case 39: // right
	viewModalNext();
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
    });
}

if (document.URL.indexOf("?") < 0) {
    listName = "all"
} else {
    listName = document.URL.split("?")[1]
}

document.body.onscroll = scrollHook;
document.body.onhashchange = hashChangeHook;

loadPromise = Promise.all([
    getJSON("/list/" + listName).then(function(listEditable) {
	photoList = listEditable[0]
	editable = listEditable[1]
	if (!editable) {
	    editableOnlyButtons.forEach(function(button) {
		button.style.display = "none";
	    });
	}
    }),
    getJSON("/albums").then(function(albumNames) {
	albums = albumNames;
    }),
    getJSON("/username").then(function(username) {
	setUsername(username);
    })
])

loadPromise.then(function() {
    reflow();
    loadChunk();
});


