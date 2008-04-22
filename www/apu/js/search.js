var tabCount = 0;
var currentSortSide = null;
var currentSortWord = null;
var currentTab = null;
var tabArray = new Array();



Rico.loadModule('LiveGridAjax'); 
Rico.loadModule('LiveGridMenu');
Rico.include('../css/greenHdg.css');
Rico.loadModule('Accordion');

var searchOpts = {  
	//menuEvent     : 'dblclick',			
	canSortDefault: false,
	canHideDefault: true,
	allowColResize: true,
	canFilterDefault: true,
	highlightElem: 'none',
	columnSpecs: [,{ClassName: 'leftKwic'},{ClassName: 'node'},{ClassName:'rightKwic'}]
};


function setCurrentTab(tabID){
	currentTab = tabID;
	
}


function getIndexList(){
	var url = '/apu' + '?operation=browse&mode=index';
	//alert(url)
	new Ajax.Request(url, {method: 'get', asynchronous: false, 		
	    onSuccess: function(transport) { 
	    	var response = transport.responseText;
	    	var options = response.substring(5,response.indexOf('</xml>'));
		var select = ($('indexSelect'))
		select.innerHTML = options;
	    }	    
	 });
}


function doSort(side, number){
	var rsid = tabArray[currentTab];
	//alert('current rsid is ' + rsid + ' & current tab is ' + currentTab);
	currentSortSide = side;
	currentSortWord = number;	
	var url = '/apu/?' + 'operation=search&mode=sort&id=' + rsid + '&side=' + side + '&wordNumber=' + number;
	var pars = 'operation=search&mode=sort&id=' + rsid + '&side=' + side + '&wordNumber=' + number; 
	new Ajax.Request(url, {method: 'get', asynchronous: false, onSuccess: function(transport) { 
		var response = transport.responseText;
		showGrid(currentTab, rsid);
	}});			
}


/* for AJAX Rico LiveGrid KWIC display */
function doSearch() {
	var label = 'kwic_grid_';
	var form = $('searchForm');   
	if(form.terms.value == ''){
		alert('Enter Search Term');
	}
	else {
		//tabID = addTab('tabs',$('terms').value);
		tabID = addSearchTab($('terms').value);
		
		var searchTabID = 'tab' + (parseInt(tabID.substr(3)) + 3);
		var viewTabID = (parseInt(tabID.substr(3)) + 2);	
		var kwicTabID = viewTabID + 1;
		var resultsTabID = viewTabID-1;
		//alert(searchTabID);

		/* first do ajax call to search handler to get a rsid 
		   then use that rsid as the ID attribute on table below
		*/
		pars = '?' + form.serialize();
		var url = '/apu'+pars;
		var div = $('tabWidget');


		// UPDATE THE RESULTS DIV WITH SUMMARY OF SEARCH PARAMETERS
		var searchDiv = $('results'+resultsTabID);
		
		var context = pars.replace(/^.*context=([^&]+)&?.*$/,'$1');
		var type = pars.replace(/^.*type=([^&]+)&?.*$/,'$1');
		var span = pars.replace(/^.*span=([^&]+)&?.*$/,'$1');
		var terms = pars.replace(/^.*terms=([^&]+)&?.*$/,'$1');
		terms = terms.replace(/%20/g,' ');
		terms = terms.replace(/%7B/g,'{');
		terms = terms.replace(/%7D/g,'}');
		terms = terms.replace(/%5B/g,'[');
		terms = terms.replace(/%5D/g,']');
		terms = terms.replace(/%3C/g,'&lt;');
		terms = terms.replace(/%3E/g,'&gt;');

		/* BROKEN
		var searchUnit = context;
		if (context == 'sentence' || context == 'paragraph' || context == 'article') {
			searchUnit = searchUnit+"s";
		} else if (context=='window') {
			searchUnit = 'sentences';
		} else {
			searchUnit = context + ' sentences';
		}

		searchUnit = " " + searchUnit;
		*/
		var searchUnit = " articles";

		if (context == 'window') {
			context = 'a window of ' + span + ' words';
		} else if (context == 'sentence' || context == 'paragraph' || context == 'article') {
			if (type == 'phrase' || terms.indexOf(' ')==-1) {
				if (context == 'article') {
					context = 'an ' + context;
				} else {
					context = 'a ' + context;
				}
			} else {
				context = 'the same ' + context;
			}
		} else {
			context = 'the subcorpus ' + context;
		}

		if (type == 'phrase') {
			type = "the " + type;
		} else {
			type = type + " of";
		}


		var summary = "Searching for <i>" + type + "</i> <b>" + terms + "</b> in <u>"+ context + "</u>";
		var summarySpan = document.createElement('span');
		summarySpan.innerHTML = summary;

		var searchSummary = document.createElement('div');
		searchSummary.appendChild(summarySpan);
		searchDiv.appendChild(searchSummary);
		
		new Ajax.Request(url, {method: 'get', asynchronous: true, 
		    onSuccess: function(transport) { 
		    	var response = transport.responseText;
		    	var rsid = response.substring(response.indexOf('<rsid>')+6,response.indexOf('</rsid>'));
			var totalDocs = response.substring(response.indexOf('<totalDocs>')+11,response.indexOf('</totalDocs>'));
			
			var totalOccs = response.substring(response.indexOf('<totalOccs>')+11,response.indexOf('</totalOccs>'));
			if (rsid != 'None'){
				if (totalDocs > 0){				
					//$('results' + (parseInt(tabID.substr(3))+ 1)).innerHTML = rsid;
					var searchResults = document.createElement('div');
					searchResults.appendChild(document.createTextNode('Hits found in ' + totalDocs + searchUnit));
					searchDiv.appendChild(searchResults);
					setUpView(viewTabID, rsid, totalDocs);
					buildConcordance(kwicTabID, rsid);
	
				}
				else {
					alert('no results');
					
				}
			}
		    }	    
		});
	}
}

function showGrid(tabID, rsid){

	
	//alert('In showGrid with ' + tabID + ' ' + rsid);
    	var pars = '?operation=search&mode=search&gid=' + rsid;
    
    	var url = '/apu'+pars;
    	//alert(url);
    	var tabHTML = '<div><p class="ricoBookmark"><span id="kwic_grid_' + rsid + '_bookmark">&nbsp;</span></p>' +
    			  '<table id="kwic_grid_' + rsid + '" class="ricoLiveGrid"  cellspacing="0" cellpadding="0" >' +
    			  ' <colgroup><col style="width:40px;" ><col style="width:300px; color: red;" ><col style="width:80px;" ><col style="width:300px;" ></colgroup> ' +
			   	  '<tr id="kwic_grid_' + rsid + '_main">' +
	  		      '<th>#</th><th class="leftHead">Left</th><th class="nodeHead">Node</th><th class="rightHead">Right</th>' +
	  		      '</tr></table></div>';

	
    var div = $(tabID);
    //alert(div + ' ' + tabHTML);
    div.innerHTML=tabHTML;

    createLiveGridSearch(url, tabID, rsid);
}



function createLiveGridSearch(url, tabID, rsid){
	
	var params = {
			TimeOut:20000,
			requestParameters:[{name:'filter',value:'false'}]
			};
  	var gridCode = "kwicGrid" + tabID + " = new Rico.LiveGrid ('kwic_grid_" +rsid+"', new Rico.Buffer.AjaxSQL('" + url + "', params, opts) , searchOpts); kwicGrid"+ tabID +".menu=new Rico.GridMenu({});"
	tabArray[tabID] = rsid;
	setCurrentTab(tabID);
	eval(gridCode);
	
}


function navigate(rsid,start, tabID) {

    	var url = '/apu';

	var div = $(tabID);
 	div.innerHTML='<div>Loading.....</div>';
    	var pars = 'operation=search&mode=search&rsid='+rsid+'&start='+start;
    	var myAjax = new Ajax.Updater(div, url, {method:'get',parameters:pars, asynchronous: true});
}

function getArticle(parent) {
	   
    var url = '/apu';
	var pars = 'operation=search&mode=article&parent='+parent;
	var div = $('article');
	$('resultTabWidget').tabber.tabShow(1);
	div.innerHTML='<div>Loading.....</div>';
    var myAjax = new Ajax.Updater(div, url, {method:'get',parameters:pars, asynchronous: true});
}


// searchFor function populates the search form with passed 
// values and does a search
// used for links in browse tables
// added MBOD 5/12/07
// adapted to work for Ngrams CJS 17/01/08
function searchFor(terms, context) {
	
	// c2 is id for the search tab and its contents (i.e. the form is tab 2)
	// make it visible
	var c = confirm('Search for "' + terms + '" in '+ context + '?');
		
	if (c) {		
		showTab($('c2'),'2');
		var termArray = terms.split(' ');
		if (termArray.length > 1){
			$('type_phrase').checked=true;	
		}
		else {
			$('type_any').checked=true;
		}
		$('terms').value=terms;
		$('context_'+context).checked=true;
		doSearch();
	}
}

function getCFP(term){
    
    var url = '/apu/?operation=search&mode=cfp&term=' + term;
   
    reloadPopup();
    popupTitle("CFP: " + term);	     	

    new Ajax.Request(url, {method: 'get', asynchronous: true, 		
	    onSuccess: function(transport) { 
	    	var response = transport.responseText;		showPopup(response);
		//tfp.innerHTML = response;
		//div.appendChild(tfp);
	    }	    
	 });
}

function buildConcordance(tabID, rsid){
	var resultsTab = tabID-2;
	
	var url = '/apu/?operation=search&mode=concordance&id=' + rsid;	
	
	new Ajax.Request(url, {method: 'get', asynchronous: true, 		
	    onSuccess: function(transport) { 
		var response = transport.responseText;
	
		var lines = response.substring(12,response.indexOf('</lines>'));
		
				
		var msg = 'Total Number of Hits found: ' + lines;
		var rDiv = document.createElement('div');
		rDiv.appendChild(document.createTextNode(msg));

		$('t'+tabID).setAttribute('rsid',rsid);
		$('t'+tabID).className = '';
		$('results' + resultsTab).appendChild(rDiv);

		// if there is syntax table add to results
		if (response.indexOf('<table')!=-1) {
			var table=response.substring(response.indexOf('<table'), response.indexOf('</xml>'));
			var tableDiv = document.createElement('div');
			tableDiv.innerHTML = table;
			$('results' + resultsTab).appendChild(tableDiv);
		}

		buildCollocates(tabID+1, rsid, lines);		
		
	    }
	});
	
}

function showConcordance(tabID, rsid) {
	if ($('t' + tabID).className == 'deactivated'){
		return;
	}
	//alert('show conc: ' + tabID + ' ' + rsid);
	showGrid('tab'+tabID, rsid);
}
