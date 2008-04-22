


var tabCount=0;

function activateTabs(id) {

	var tabs = $(id).getElementsByTagName('li');
	
	for (var i=0; i<tabs.length; i++) {
	
		var tabID = id.substr(0,id.length-1) + (i+1);
	
		Event.observe(tabs[i].id,'click', function(event) { showTab(Event.element(event), Event.element(event).id.substr(1)); });
	
		tabCount++;
	
	}
	
}

function showTab(tab, tabID) {

	if (tab.className == 'deactivated'){
		return;
	}


	// set the current tab variable
	// if this is a top level tab then look at tabs it contains
	// the currently selected one will be given to currentTab
	if (tabID>2) {
	/*
		var innerTabs = $('tab'+tabID).getElementsByClassName('tab_selected');
		if (innerTabs.length>0) {
			alert(innerTabs[0].id);
		} else {
			setCurrentTab('tab'+tabID);
		}
	*/

		setCurrentTab('tab'+tabID);
	}


	// hide the popup window
	hidePopup();

	var tabBlock=tab.parentNode.parentNode.parentNode;

	

	var tid = tab.parentNode.parentNode.id;
	
	var currentTab = tid.substr(0,tid.length-1)+tabID;
	

	var prefix = tid.substr(0,tid.indexOf("_"));

	var tabID = $(prefix+tabID);
	


	// clear selected tab


	
	var tabs = tabBlock.getElementsByTagName('li');
	
	for (var i=0; i<tabs.length; i++) {
	
		if (tabs[i].className != 'deactivated' && tabs[i].parentNode.parentNode.parentNode == tabBlock) {
			
			tabs[i].className='';
		}	
	}
	
	// hide all tabCanvas
	
	var canvas = tabBlock.getElementsByClassName('tab_visible');
	

	for (var i=0; i<canvas.length; i++) {
		if (canvas[i].parentNode.parentNode == tabBlock) {
			canvas[i].className='tabCanvas';
		}	
	}
	
	// make calling tab selected
	
	tab.className='tab_selected';
	
	// show canvas for selected tab
	
	tabID.className='tab_visible tabCanvas';
	


}

function addTab(tabBlock,label,container) {
	
	
	if (container == undefined) { container=''; }

	
	var tabContainer = $(tabBlock).getElementsByTagName('ul')[0];
	
	var canvasContainer = $('canvasContainer'+container);
	
	tabCount++;
	
	var tid = 't'+tabCount;

	var newTab = document.createElement('li');

	if (label=='KWIC' || label == 'Collocates' || label == 'Associations') {
		newTab.setAttribute('activated','false');

	}
	
	newTab.id = tid;
	
	newTab.appendChild(document.createTextNode(label));
	
	tabContainer.appendChild(newTab);
	
	if (label == 'KWIC') {
		Event.observe(tid,'click', function(event) { showTab(Event.element(event), Event.element(event).id.substr(1));
		if (Event.element(event).getAttribute('activated') == 'false') { showConcordance(Event.element(event).id.substr(1), Event.element(event).getAttribute('rsid')); Event.element(event).setAttribute('activated','true');}} );
	} else if (label == 'Collocates') {
		Event.observe(tid,'click', function(event) { showTab(Event.element(event), Event.element(event).id.substr(1));
		if (Event.element(event).getAttribute('activated') == 'false') { showCollocates(Event.element(event).id.substr(1), Event.element(event).getAttribute('rsid')); Event.element(event).setAttribute('activated','true');}} );

	} else if (label == 'Associations') {
		Event.observe(tid,'click', function(event) { showTab(Event.element(event), Event.element(event).id.substr(1));
		if (Event.element(event).getAttribute('activated') == 'false') { showArmTable(Event.element(event).id.substr(1), Event.element(event).getAttribute('rsid')); Event.element(event).setAttribute('activated','true');}} );

	} else {
		Event.observe(tid,'click', function(event) { showTab(Event.element(event), Event.element(event).id.substr(1)); });
	} 	

	var tabCanvas = document.createElement('div');
	
	tabCanvas.className='tabCanvas';
	
	tabCanvas.id='tab'+tabCount;
	
	canvasContainer.appendChild(tabCanvas);
	
	showTab(newTab,tabCount);

	if (label == 'View' || label=='KWIC' || label == 'Collocates' || label == 'Associations') {
		
		newTab.className = 'deactivated';
	}

	// return tabID
	return 'tab'+tabCount;

}

function addSearchTab(label) {

	searchTabID = addTab($('tab_'), label);
		

	var innerTabBlock = document.createElement('div');
	innerTabBlock.className = 'tabs';
	innerTabBlock.id = 'tab_B' + searchTabID.substr(3);
	innerTabBlock.appendChild(document.createElement('ul'));
	
	var innerTabCanvas = document.createElement('div');
	innerTabCanvas.id='canvasContainer'+searchTabID;

	var currentTabCanvas = $(searchTabID);
	var tabWidget = document.createElement('div');
		
	currentTabCanvas.appendChild(tabWidget);
	
	
	tabWidget.appendChild(innerTabBlock);
	tabWidget.appendChild(innerTabCanvas);

	var resTabID = addTab(innerTabBlock.id,'Results',searchTabID);
	var artTabID = addTab(innerTabBlock.id,'View',searchTabID);
	var kwicTabID = addTab(innerTabBlock.id,'KWIC',searchTabID);
	
	var colTabID = addTab(innerTabBlock.id,'Collocates',searchTabID);	
	var armTabID = addTab(innerTabBlock.id,'Associations',searchTabID);
	
	var resNum = (tabCount-4);

	showTab($('t'+resNum),resNum);

	var canvas = $('tab' + (resNum));
			
	var results = document.createElement('div');
	results.id = 'results' + resNum;
	results.className = 'resultsSummaries';
	
	canvas.appendChild(results);

	var vNum = resNum + 1;
	
	var nav = document.createElement('div');
	nav.id = 'navigate' + vNum;
	var view = document.createElement('div');
	view.id = 'viewpane' + vNum;

	var vCanvas = $('tab' + vNum);
	vCanvas.appendChild(nav);
	vCanvas.appendChild(view);

	

	return searchTabID;
}



/* POPUP WINDOW FUNCTIONS */

function showPopup(html) {
	$('popupWindow').style.display="block";
	$('popupWindowFrame').innerHTML = html;			
}

function reloadPopup() {
	$('popupWindow').style.display="block";
	popupTitle();
	$('popupWindowFrame').innerHTML = "<img src='/apu/js/images/indicator.white.gif'/>";
}

function hidePopup() {
	$('popupWindow').style.display="none";
}

function popupTitle(label) {
	$('popupTitle').innerHTML = label;
}
