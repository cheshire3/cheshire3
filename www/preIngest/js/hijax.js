/*
// Program:   hijax.js
// Version:   0.01
// Description:
//            JavaScript functions for Ajax manipulations of HTML pages.  
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
// 0.02 - 28/01/2009 - JH - useability tweaks
*/

function createXMLHttpRequest() {
	var xmlHttp=null;
	try {
		// Firefox, Opera 8.0+, Safari
		xmlHttp=new XMLHttpRequest();
	}
	catch (e) {
		// Internet Explorer
		try {
			xmlHttp=new ActiveXObject("Msxml2.XMLHTTP");
			}
		catch (e) {
			try {
		    	xmlHttp=new ActiveXObject("Microsoft.XMLHTTP");
		    }
			catch (e) {
			    alert("Your browser does not support AJAX! Some functionality will be unavailable.");
			    return false;
		    }
		}
	}
	return xmlHttp;
}

function updateElementByUrl(id, url) {
	if( !document.getElementById) {
		window.alert("Your browser does not support functions essential for updating this page with AJAX!")
		return true;
	}
	var el = document.getElementById(id);
	// first obscure target to avoid repeat clicks
	displayLoading(el);
	var xmlHttp = createXMLHttpRequest();
	if (xmlHttp==null) {
		alert ("Your browser does not support AJAX!");
		return true;
	}
	xmlHttp.onreadystatechange=function() {
		if(xmlHttp.readyState==4) {
			if (xmlHttp.status == 200 || xmlHttp.status == 304) {
				el.innerHTML=xmlHttp.responseText;
				ajaxifyLinks(el);
				try {
					fadeToWhite(el, 196, 214, 248);
				} catch(err) {
				}
			}
		}
	}
	xmlHttp.open("GET",url,true);
  	xmlHttp.send(null);
  	return false;
}

function displayLoading(el) {
	el.innerHTML = '<div class="loading"><img src="../images/ajax-loader.gif" alt=""/></div>';
}

function ajaxifyLinks(el){
	if( !el.getElementsByTagName) {
  		return;
  	}
  	var linkList = el.getElementsByTagName("a");
	for (var i = 0; i < linkList.length; i++) {
		var el = linkList[i]
		if (el.className.match('ajax')){
			el.onclick = function() {
				var hrefParts = this.getAttribute("href").split("#")
				var div = hrefParts.pop()
				hrefParts.push("&ajax=1")
				return updateElementByUrl(div, hrefParts.join(""));
				
			}
		}
	}
}

olf = function() { ajaxifyLinks(document);};
if (addLoadEvent) {
	addLoadEvent(olf);
} else {
	window.onload = olf;
}
