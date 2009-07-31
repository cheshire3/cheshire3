/*
// Program:   visuals.js
// Version:   0.01
// Description:
//            JavaScript functions for creating visual effects on HTML pages  
//            - produced for the Archives Hub v3.0
//
// Language:  JavaScript
// Author:    John Harrison <john.harrison@liv.ac.uk>
// Date:      28/07/2008
//
// Copyright: &copy; University of Liverpool 2005-2008
//
// Version History:
// 0.01 - 28/07/2008 - JH - functions scripted
//
*/

function fadeToWhite(element,red,green,blue) {
  if (element.fade) {
    clearTimeout(element.fade);
  }
  element.style.backgroundColor = "rgb("+red+","+green+","+blue+")";
  if (red == 255 && green == 255 && blue == 255) {
    return;
  }
  var newred = red + Math.ceil((255 - red)/10);
  var newgreen = green + Math.ceil((255 - green)/10);
  var newblue = blue + Math.ceil((255 - blue)/10);
  var repeat = function() {
    fadeToWhite(element,newred,newgreen,newblue)
  };
  element.fade = setTimeout(repeat,10);
}

linkHash = new Array();
linkHash['text'] = new Array('[ show ]', '[ hide ]');
linkHash['plusMinus'] = new Array('[+]', '[-]');
linkHash['folders'] = new Array('<img src="/ead/img/folderClosed.gif" alt="[+]"/>', '<img src="/ead/img/folderOpen.gif" alt="[-]"/>');

function toggleShow(callLink, elementId, toggleStyle){
	if( !document.getElementById) {
		return;
	}
	if (typeof toggleStyle == "undefined") {
    	toggleStyle = "text";
  	}
	e = document.getElementById( elementId );
	if (e.style.display == 'block') {
		callLink.innerHTML = linkHash[toggleStyle][0];
		e.style.display = 'none';
	} else {
		callLink.innerHTML = linkHash[toggleStyle][1];
		e.style.display = 'block';
	}
	return;
}

function hideStuff(){
	if( !document.getElementsByTagName) {
  		return;
  	}
  	var linkList = document.getElementsByTagName("a");
	for (var i = 0; i < linkList.length; i++) {
		var el = linkList[i]
		if (el.className.match('jstoggle')){
			var classBits = el.className.split('-')
			var toggleStyle = classBits[classBits.length-1]
			el.innerHTML = linkHash[toggleStyle][0]
			el.onclick = function() {
				var hrefParts = this.getAttribute("href").split("#")
				var div = hrefParts.pop()
				var classBits = this.className.split('-')
				var style = classBits[classBits.length-1]
				toggleShow(this, div, style);
				return false;
			}
		}
	}
	var divList = document.getElementsByTagName("div");
	for (var i = 0; i < divList.length; i++) {
		var el = divList[i]
		if (el.className.match('jshide')){
			el.style.display = 'none';
		}
	}
}

if (addLoadEvent) {
	addLoadEvent(hideStuff);
} else {
	window.onload = hideStuff;
}
