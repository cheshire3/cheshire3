var indexCount = 0;
var tabCount = 0;
var currentIndexSelected = null;
var filterStart = 0;

	Rico.loadModule('LiveGridAjax');
	Rico.loadModule('LiveGridMenu');
	Rico.include('greenHdg.css');
			


     var opts = {  
			
	allowColResize: true,
	highlightElem: 'none',
	};


	var orderGrid = [];


function showWordList() {

	var form = $('browseform');
        var pars = '?operation=browse&mode=list&' + form.serialize();
        var url = '/apu' + pars;
	var index = [$('indexSelect').value];
	
	addIndexTab(index);
	createLiveGrid(url,tabCount);
}


function createComparison(){
	
	var form = $('browseform');
    	var pars = '?operation=browse&mode=compare&' + form.serialize();
    	var url = '/apu' + pars;
	var index = document.getElementsByName('index');
	var name = [];
        if (index.length == 0) {
	alert("error no index selected");
	exit;
	}
	for (var i=0; i<index.length; i++){
		
	    name.push(index[i].value );
	}

	if (index.length < 2 && index.length > 0  ){
   	  name.push("Raw Freq. from Data");			
      	}
	
    ($('box')).innerHTML = '';
    getIndexList()
    indexCount = 0;

	addIndexTab(name);
	createLiveGrid(url,tabCount);
}



function createLiveGrid(url,tabID){
   	
	var params = {
			TimeOut:20000,
			requestParameters:[{name:'filter',value:'true'}]
			};
  	var gridCode = "orderGrid" + tabID + " = new Rico.LiveGrid ('browse_grid_"+tabID+"', new Rico.Buffer.AjaxSQL('" + url + "', params, opts));" 

	eval(gridCode);		
} 
	


function unselectCurrent(){
	if (currentIndexSelected != null){
		($(currentIndexSelected)).className = 'notSelected';
		currentIndexSelected = null;
	}	
}	
	
	
function select(id){
    unselectCurrent();
    ($(id)).className = 'selected';
	currentIndexSelected = id;
}	


function addIndex(){
    var box = $('box');
    var select = $('indexSelect');
    var index = select.value;
	
    if (select.disabled != true && index != 'none'){

	    updateList();
	    
	    var words = document.createElement('div');    
	    words.setAttribute('id', 'index' + indexCount);
	    words.setAttribute('onclick', 'select(this.id);');
	    words.appendChild(document.createTextNode(index.substring(0, index.lastIndexOf('-'))));
	    box.appendChild(words);
	    
	    var input = document.createElement('input');
	    input.setAttribute('type', 'hidden');
	    input.setAttribute('name', 'index');
	    input.setAttribute('id', 'hidden-index' + indexCount);
	    input.setAttribute('value', index);
	    box.appendChild(input);
	    unselectCurrent();
	
	    indexCount++;   
	    
    }
    var test = false;
    var i = 0;
    while (test == false && i < select.options.length){
	if (select.options[i].disabled != true){	
    	    select.options[i].selected = true;
	    test = true;	
	}
	else {
	    i++;
	}
    }
    if (test == false){
	var newopt = document.createElement('option');
	newopt.text = 'no indexes'
	newopt.value = 'none';  
	try {
	  select.add(newopt, select.options[0]); // standards compliant; doesn't work in IE
	  select.options[0].selected = true;
	}
	catch(ex) {
	  select.add(newopt, select.selectedIndex); // IE only
	}
    }
}


function tfpFor(word, indexName){

    //div = ($('tfp_' + currentTab));
    //div.innerHTML = '';
    
    reloadPopup();
    popupTitle('TFP: ' + word);

    var url = '/apu/?operation=browse&mode=tfp&index=' + indexName + '&word=' + word;
    	
    new Ajax.Request(url, {method: 'get', asynchronous: true, 		
	    onSuccess: function(transport) { 
	    	var response = transport.responseText;
		//tfp.innerHTML = response;
		showPopup(response);
		//div.appendChild(tfp);
	    }	    
	 });
}

function setFilterStart(value){
	filterStart = value;
	alert('filter start = ' + value);
}	

function updateList(){

    var select = $('indexSelect');
    var index = select.value;
    var number = select.options[select.selectedIndex].getAttribute('class');
    select.options[select.selectedIndex].disabled = true;
    for (var i=select.options.length-1; i>=0; i--){
	if (select.options[i].getAttribute('class') != number){
	    select.options[i] = null;
	}
    }
}


function removeIndex() {

	var value = ($('hidden-' + currentIndexSelected)).value;
	($(currentIndexSelected)).remove();
	
	($('hidden-' + currentIndexSelected)).remove();
	var box = ($('box'))
	currentIndexSelected = null;
	var indexes = 0;
	for (var i=0; i<box.childNodes.length; i++){
		if (box.childNodes[i].tagName=='DIV' || box.childNodes[i].tagName=='INPUT'){
			indexes +=1;			
		}
	}
	if (indexes == 0){
		getIndexList();
	}
	else {
		var select = $('indexSelect');
		for (var i=select.options.length-1; i>=0; i--){
			if (select.options[i].value == value){
	    			select.options[i].disabled = false;
			}
    	    	}		
	}	
}



function addIndexTab(indexes) {
	
	var label = "";	
	for (i=0; i<indexes.length; i++) {
		if (indexes[i] != "Raw Freq. from Data") { 
			label += indexes[i].substring(0, (indexes[i].length)-4);
			if (i<indexes.length-1 && indexes[i+1] != "Raw Freq. from Data") { label+=', ';}
		}	
	}
	if (label.length > 30){
		label = label.substring(0, 30) + '...'
	}
	
	addTab('tab_',label);

	var tabHTML = '<div><p class="ricoBookmark"><span id="browse_grid_' + tabCount + '_bookmark">&nbsp;</span></p>' +
				  '<table id="browse_grid_' + tabCount + '" class="ricoLiveGrid"  cellspacing="0" cellpadding="0" >' +
    			  ' <colgroup><col style="width:40px;" ><col style="width:300px;" > ';
    			  
	for (i=0; i<indexes.length; i++) {
			tabHTML += '<col style="width:80px;">';
	}
	
	tabHTML += '</colgroup>' +
			   '<tr id="browse_grid_' + tabCount + '_main">' +
	  		   '<th>#</th><th>term from ' +  indexes[0].substring(0, (indexes[0].length)-4) + '</th>'
	if (indexes[0].indexOf('gram') == -1){
		tabHTML += '<th>TFP</th>';
	}
	

	for (i=0; i<indexes.length; i++) {
		if (indexes[i] == "Raw Freq. from Data") { 
			
			tabHTML += '<th>' + indexes[i] + '</th>'
		} else {
			tabHTML += '<th>' + indexes[i].substring(0, (indexes[i].length)-4)  + ' freq. per 1000 words</th>';
		}	
	}	
	  		 
	tabHTML += '</tr></table></div>'; // <textarea cols="100" rows="20" id="browse_grid_'+tabCount+'_debugmsgs" /></div>';																																											
	
	html = document.createElement('span');
	html.className = 'float';
	html.innerHTML = tabHTML;
	
	//tfp = document.createElement('span');
	//tfp.className = 'tfp_table';	
	//tfp.setAttribute('id', 'tfp_tab' + tabCount);
	tabs = $('tab'+tabCount);
	
	tabs.appendChild(html);
	//tabs.appendChild(tfp);

}
