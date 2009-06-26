/*
// Script:   counter.js
// Version:   0.01
// Description:
// 	functions to allow onscreen counter objects
*/

function incr(elementId) {
	if( !document.getElementById) {
		return;
	}
	var e = document.getElementById( elementId );
	var i = parseInt(e.innerHTML)
	i++
	e.innerHTML = i	
}

function decr(elementId) {
	if( !document.getElementById) {
		return;
	}
	var e = document.getElementById( elementId );
	var i = parseInt(e.innerHTML)
	i--
	e.innerHTML = i
}
