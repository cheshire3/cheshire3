
var tabCount = 0;


	Rico.loadModule('LiveGridAjax');
			Rico.loadModule('LiveGridMenu');
			Rico.include('greenHdg.css');
			


     var opts2 = {  
		
		canSortDefault: true,
		canHideDefault: true,
		allowColResize: true,
		allowRowResize: true,
		canFilterDefault: true,
		highlightElem: 'none',
		filterImg: 'sort_asc.gif',

		

	};


	var orderGrid = [];


function showCollocateTable(tabID,id) {

    var pars = '?operation=search&mode=collocates';
    var url = '/apu' + pars;


	cols = 10;

	var tabHTML = '<div><p class="ricoBookmark"><span id="collocate_grid_' + id + '_bookmark">&nbsp;</span></p>' +
				  '<table id="collocate_grid_' + id + '" class="ricoLiveGrid"  cellspacing="0" cellpadding="0" >' +
    			  '<colgroup><col style="width:40px;" > <col style="width:150px;" > ';
    			  
	for (i=0; i<cols+3; i++) {
			tabHTML += '<col style="width:50px;" > ';
	}
	
	tabHTML += '</colgroup>' +
			   '<tr id="collocate_grid_' + id + '_main">' +
	  		   '<th>#</th><th>word</th><th>TOTAL</th><th>Left</th><th>Right</th>';

	for (i=0; i<cols; i++) {
		label=""
		if (i < cols/2) {
			label="L" + (5-i);
		} else {
			label="R" + (i-4);
		}
		
		tabHTML += '<th>' + label + '</th>';
	}	
	  		 
	tabHTML += '</tr></table></div>'; 
	//<textarea cols="100" rows="20" id="collocate_grid_'+id+'_debugmsgs" /></div>';																																											
	
	//html = document.createElement('span');
	//html.innerHTML = tabHTML;

	tabs = $(tabID);
	tabs.innerHTML=tabHTML;

	createLiveGrid2(url,tabID,id);

}



function createLiveGrid2(url,tabID,id){
   	var params = {
			TimeOut:20000,
			requestParameters:[{name:'filter',value:'false'}]
			};

  	var gridCode = "orderGrid" + tabID + " = new Rico.LiveGrid ('collocate_grid_"+id+"', new Rico.Buffer.AjaxSQL('" + url + "', params, opts) , opts2); "; 

	eval(gridCode);		

}
	





function buildCollocates(tabID, rsid, totalHits){
	var resultsTab = tabID-3;
	
	var url = '/apu/?operation=search&mode=collocates&gid=' + rsid;	
	
	new Ajax.Request(url, {method: 'get', asynchronous: true, onSuccess: function(transport) { 
		var response = transport.responseText;
		var rsid = response.substring(6,response.indexOf('</rsid>'));	
		//alert('collocate table built! for ' + tabID);		
		$('t'+tabID).setAttribute('rsid',rsid);
		$('t'+tabID).className = '';
		var context = rsid.substr(0, rsid.indexOf('|'));
		if (context == 'sentence' || context == 'TISC' || context == 'PISC' || context == 'SISC' || context == 'NISC'){
				if (totalHits > 400){
					buildArm(tabID+1, rsid);
				}				
			
		}
		    
	}});
	
}

function showCollocates(tabID, rsid) {
	if ($('t' + tabID).className == 'deactivated'){
		return;
	}
	//alert('show colls: ' + tabID + ' ' + rsid);
	showCollocateTable('tab'+tabID, rsid);
}


