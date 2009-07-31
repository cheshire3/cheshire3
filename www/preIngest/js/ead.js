/*
// Program:   ead.js
// Version:   0.10
// Description:
//            JavaScript functions used in the Cheshire3 EAD search/retrieve and display interface 
//            - part of Cheshire for Archives v3.0
//
// Language:  JavaScript
// Author:    John Harrison <john.harrison@liv.ac.uk>
// Date:      17/02/2009
//
// Copyright: &copy; University of Liverpool 2005-2009
//
// Version History:
// 0.01 - 25/05/2005 - JH - Nested list ToC manipulation functions scripted
// 0.02 - xx/06/2005 - JH - Rudimentary splash screen added
// 0.03 - 21/10/2005 - JH - Cookie support added to maintain state of expanded list when page is unloaded
// 0.04 - 04/01/2006 - JH - E-mail addresses checked before submission to save server time
// 0.05 - 18/06/2006 - JH - TOC state cookie stuff debugged
// 												- Search form manipulation to add more clauses
// 0.06 - 03/08/2006 - JH - Non EAD specific functions separated into aptly named files in a separate javascript dir
// 0.07 - 15/05/2007 - JH - toggleShow function added
// 0.08 - 23/07/2008 - JH - function stacks implemented using Simon Willison's addLoadEvent
// 0.09 - 26/09/2008 - JH - Visual effects (show/hide) superceded by those in visuals.js - removed
// 0.10 - 17/02/2009 - JH - Array prototype stuff added for standard functionality in v. old browsers (IE<5.5)
*/ 

Array.prototype.indexOf=function(n){for(var i=0;i<this.length;i++){if(this[i]===n){return i;}}return -1;}
Array.prototype.lastIndexOf=function(n){var i=this.length;while(i--){if(this[i]===n){return i;}}return -1;}
Array.prototype.forEach=function(f){var i=this.length,j,l=this.length;for(i=0;i<l;i++){if((j=this[i])){f(j);}}};
Array.prototype.insert=function(i,v){if(i>=0){var a=this.slice(),b=a.splice(i);a[i]=value;return a.concat(b);}}
Array.prototype.shuffle=function(){var i=this.length,j,t;while(i--){j=Math.floor((i+1)*Math.random());t=arr[i];arr[i]=arr[j];arr[j]=t;}}
Array.prototype.unique=function(){var a=[],i;this.sort();for(i=0;i<this.length;i++){if(this[i]!==this[i+1]){a[a.length]=this[i];}}return a;}
if(typeof Array.prototype.concat==='undefined'){Array.prototype.concat=function(a){for(var i=0,b=this.copy();i<a.length;i++){b[b.length]=a[i];}return b;};}
if(typeof Array.prototype.copy==='undefined'){Array.prototype.copy=function(a){var a=[],i=this.length;while(i--){a[i]=(typeof this[i].copy!=='undefined')?this[i].copy():this[i];}return a;};}
if(typeof Array.prototype.pop==='undefined'){Array.prototype.pop=function(){var b=this[this.length-1];this.length--;return b;};}
if(typeof Array.prototype.push==='undefined'){Array.prototype.push=function(){for(var i=0,b=this.length,a=arguments;i<a.length;i++){this[b+i]=a[i];}return this.length;};}
if(typeof Array.prototype.shift==='undefined'){Array.prototype.shift=function(){for(var i=0,b=this[0];i<this.length-1;i++){this[i]=this[i+1];}this.length--;return b;};}
if(typeof Array.prototype.slice==='undefined'){Array.prototype.slice=function(a,c){var i=0,b,d=[];if(!c){c=this.length;}if(c<0){c=this.length+c;}if(a<0){a=this.length-a;}if(c<a){b=a;a=c;c=b;}for(i;i<c-a;i++){d[i]=this[a+i];}return d;};}
if(typeof Array.prototype.splice==='undefined'){Array.prototype.splice=function(a,c){var i=0,e=arguments,d=this.copy(),f=a;if(!c){c=this.length-a;}for(i;i<e.length-2;i++){this[a+i]=e[i+2];}for(a;a<this.length-c;a++){this[a+e.length-2]=d[a-c];}this.length-=c-e.length+2;return d.slice(f,f+c);};}
if(typeof Array.prototype.unshift==='undefined'){Array.prototype.unshift=function(a){this.reverse();var b=this.push(a);this.reverse();return b;};}


function addLoadEvent(func) {
	var oldonload = window.onload;
	if (typeof window.onload != 'function') {
    	window.onload = func;
	} else {
	window.onload = function() {
			if (oldonload) {
				oldonload();
			}
			func();
		}
	}
}

function addUnloadEvent(func) {
	var oldonunload = window.onunload;
	if (typeof window.onunload != 'function') {
    	window.onunload = func;
	} else {
	window.onunload = function() {
			if (oldonunload) {
				oldonunload();
			}
			func();
		}
	}
}



/* Splash Screen */
var splash = null;
var myBars = 'directories=no,location=no,menubar=no,status=no,titlebar=no,toolbar=no,scrollbars=no';
var myOptions = 'innerWidth=400,outerWidth=400,innerHeight=150,outerHeight=150,resizable=no';
//var myPosition = 'screenX=300, screenY=200';
var myPosition = 'left=300, top=200';

function splashScreen(){
  splash = window.open("/ead/ead-splash.html","splashScreen",myBars + ',' + myOptions + ',' + myPosition);
}

function closeSplash(){
  //splash = window.open("/ead/ead-splash.html", "splashScreen", myBars + ', height=1, width=1, left=1024, top=1024');
  if (splash) {
  	splash.close();
  	splash = null;
  }
}

var op = null;

function confirmOp(){
	switch(op) {
		case 'unindex':
			var msg = 'This operation will PERMANENTLY remove the file from the hard-disk. The record will also be removed from all indexes, which may take some time. Are you sure you wish to continue?';
			break
		case 'delete':
			var msg = 'This operation will PERMANENTLY remove the file from the hard-disk. Are you sure you wish to continue?';
			break
			
		default:
			if (arguments.length == 1){
				/*hopefully a message we should send*/
				var msg = arguments[0];
			}
			break
	}
	if (msg) {
		if (window.confirm) { return window.confirm(msg); }
		else if (confirm) { return confirm(msg); }
		else { return true; } // no mechanism for confirmation supported by browser - go ahead anyway
	} else {return true; } // no requirement for confirmation
}
