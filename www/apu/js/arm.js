
function buildArm(tabID, rsid){
	//alert('building ARM: tabid = ' + tabID + ' rsid = ' + rsid);
	pars = '?operation=search&mode=arm&id=' + rsid;
	 
	var url = '/apu'+pars;

	new Ajax.Request(url, {method: 'get', asynchronous: true, onSuccess: function(transport) { 
		var response = transport.responseText;
	    	var rsid = response.substring(6,response.indexOf('</rsid>'));
		$('t'+tabID).setAttribute('rsid',rsid);
		$('t'+tabID).className = '';
		//alert('ARM built');
	}});
}



function showArmTable(tabID, id) {
	if ($('t' + tabID).className == 'deactivated'){
		return;
	}
	//alert('getting Arm Table');
	var div = $('tab' + tabID);
	div.innerHTML = '<span>Loading: <img src="/apu/js/images/loading.gif"/></span>';
	pars = '?operation=search&mode=armtable&id=' + id;
	 
	var url = '/apu'+pars;	
	new Ajax.Request(url, {method: 'get', asynchronous: true, onSuccess: function(transport) { 
		var response = transport.responseText;
	    	var table = response.substring(6,response.indexOf('</rsid>'));
		if (table != 'None'){			
			
			div.innerHTML = '<p class="ricoBookmark"><span id="' + id + '_bookmark">&nbsp;</span></p>';
			
			var tableDiv = document.createElement('div');
			tableDiv.innerHTML = table;
			div.appendChild(tableDiv);
			
			var grid_options = { 
						canFilterDefault: false,
						filterImg: 'sort_asc.gif',
						columnSpecs: [ {width:70, type:'number'}, {width: 70, type:'number'}, {width:630, type:'text'} ] };
		    	var buffer = new Rico.Buffer.Base($(id).tBodies[0]);
		 
		    	var gridCode = "armGrid = new Rico.LiveGrid('" + id + "', buffer, grid_options)";

			eval(gridCode);
			
		}
	}});
}



/*

function showArmTable(tabID, table, id){

    	var div = $(tabID);
	tableDiv = document.createElement('div');
	tableDiv.innerHTML = table;
	div.appendChild(tableDiv);
	
	var grid_options = { columnSpecs: [ {width:70}, {width: 70}, {width:630} ] };
    	var buffer = new Rico.Buffer.Base($(id).tBodies[0]);
 
    	var gridCode = "armGrid = new Rico.LiveGrid('" + id + "', buffer, grid_options)";

	eval(gridCode);
}

*/

/*
function addArmTab(id) {

	var label = "associations";
	
	tabID=addTab('tabs',label);


	var tabHTML = '<div><p class="ricoBookmark"><span id="' + id + '_bookmark">&nbsp;</span></p>' +
				  '<table id="arm_grid_' + id + '" class="ricoLiveGrid"  cellspacing="0" cellpadding="0" >' +
    			  '<colgroup><col style="width:150px;" > ';
    			  
	
	tabHTML += '</colgroup>' +
			   '<tr id="' + id + '_main">' +
	  		   '<th></th><th></th><th></th>';
																																										
	tabs = $('tab'+tabCount);
	
 	tabs.innerHTML = tabHTML;
 	
 	return tabID;
	
}*/



function filterLines(tids) {
	
	
	var kwicTabID = parseInt(currentTab.substr(3)) - 2;
	
	var tab = 'tab' + kwicTabID;
	var rsid = tabArray[tab];
	showTab($('t' + kwicTabID), kwicTabID);
	$(tab).innerHTML='<span>Loading: <img src="/apu/js/images/loading.gif"/></span>';
	var url = '/apu/?' + 'operation=search&mode=filter&id=' + rsid + '&matchlist=' + tids;
	new Ajax.Request(url, {method: 'get', asynchronous: true, onSuccess: function(transport) { 
		var response = transport.responseText;
		
		showGrid(tab, rsid);
	}});	
	
}
