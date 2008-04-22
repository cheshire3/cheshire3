

function setUpView(tabID, rsid, totalDocs){
	var nav = $('navigate' + tabID);
	nav.setAttribute('rsid', rsid);	
	$('t' + tabID).className = '';

	nav.innerHTML = "<div class=\"navigation\">" +
		"<span><a href=\"javascript:navigate('" + rsid  + "', " + tabID + ", 1)\">First</a></span><span class=\"divider\">|</span>" +
		"<span><a href=\"javascript:previous('"+ rsid + "', " + tabID + ")\">Previous</a></span>" +
		"<div class=\"pageNavWidget\">Page <input id=\"pageValue" + tabID + "\" type=\"text\" value=\"1\" size=\"3\" /> of " + totalDocs +  "  <button onclick=\"navigate('" + rsid + "', " + tabID + ", -1, " + totalDocs + ");\">Go</button></div><span>" +
		"<a href=\"javascript:next('" + rsid + "', " + tabID + ", " + totalDocs + ")\">Next</a></span><span class=\"divider\">|</span>" +
		"<span><a href=\"javascript:navigate('" + rsid  + "', " + tabID + " ," + totalDocs + ")\">Last</a></span></div>";

	var loc = $('viewpane' + tabID);
	getArticle(rsid, loc, 1);
	
}


function displayArticle(rsid, pg, elem, words){
	var page = parseInt(pg) + 1;	
	var tabID = parseInt(currentTab.substr(3))-1;
	var loc = $('viewpane' + tabID);
	$('pageValue'+tabID).value = page;
	showTab(($('t' + tabID)), tabID);
	getArticle(rsid, loc, page, elem, words);	
}

function navigate(rsid, tabID, pg, totalDocs){
	if (pg != -1) {
		var page = pg;
	}
	else {
		var page = parseInt($('pageValue'+tabID).value);
	}
	if (page < 1){
		page = 1;
	}
	if (totalDocs != undefined && page > parseInt(totalDocs)){
		page = totalDocs;
	} 
	var loc = $('viewpane' + tabID);
	$('pageValue'+tabID).value = page
	getArticle(rsid, loc, page); 
	
}

function previous(rsid, tabID){
	
	var page = parseInt($('pageValue'+tabID).value);
	if (page > 1){
		page = page-1;
	}
	var loc = $('viewpane' + tabID);
	$('pageValue'+tabID).value = page;
	getArticle(rsid, loc, page); 
}


function next(rsid, tabID, totalDocs){

	var page = parseInt($('pageValue'+tabID).value);
	page = page+1;
	if (page > totalDocs){
		page = totalDocs;
	}	
	var loc = $('viewpane' + tabID);
	
	$('pageValue'+tabID).value = page
	getArticle(rsid, loc, page); 
}




function getArticle(rsid, loc, page, elem, words){
	if (elem != undefined && words != undefined){
		var url = '/apu/?operation=search&mode=article&id=' + rsid + '&page=' + page + '&elem=' + elem + '&words=' + words;
	} 
	else {
		var url = '/apu/?operation=search&mode=browse&id=' + rsid + '&page=' + page;
	}	
	loc.innerHTML="<img src='/apu/js/images/indicator.white.gif'/>";

	new Ajax.Updater(loc, url, {method: 'get', asynchronous: true, onSuccess: function(transport) {  
		
	}});
}
