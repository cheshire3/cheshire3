/*
// Program:		accesspoints.js
// Version:   	0.01
// Description:
//            	JavaScript functions for adding control access terms to Archives Hub editing interface.  
//            	- produced for the Archives Hub v3.x. 
// Language:  	JavaScript
// Author(s):   Catherine Smith <catherine.smith@liv.ac.uk>	
// Date:      	09/01/2009
// Copyright: 	&copy; University of Liverpool 2009
//
// Version History:
// 0.01 - 09/01/2009 - CS- functions completed for first release of Archives Hub editing interface
*/

    
var labelMapping = new Array();

	labelMapping['subject_subject'] = 'Subject';
	labelMapping['subject_a'] = 'Subject';
	labelMapping['subject_dates'] = 'Dates';
	labelMapping['subject_y'] = 'Dates';
	labelMapping['subject_loc'] = 'Location';
	labelMapping['subject_z'] = 'Location';
	labelMapping['subject_other'] = 'Other';
	labelMapping['subject_x'] = 'Other';
	labelMapping['subject_source'] = 'Thesaurus';
	
	labelMapping['persname_surname'] = 'Surname';	
	labelMapping['persname_a'] = 'Surname';
	labelMapping['persname_forename'] = 'Forename';
	labelMapping['persname_dates'] = 'Dates';
	labelMapping['persname_y'] = 'Dates';
	labelMapping['persname_title'] = 'Title';
	labelMapping['persname_epithet'] = 'Epithet';
	labelMapping['persname_other'] = 'Other';
	labelMapping['persname_x'] = 'Other';
	labelMapping['persname_source'] = 'Source';
	
	labelMapping['famname_surname'] = 'Surname';
	labelMapping['famname_a'] = 'Surname';
	labelMapping['famname_other'] = 'Other';
	labelMapping['famname_x'] = 'Other';
	labelMapping['famname_dates'] = 'Dates';
	labelMapping['famname_y'] = 'Dates';
	labelMapping['famname_title'] = 'Title';
	labelMapping['famname_epithet'] = 'Epithet';
	labelMapping['famname_loc'] = 'Location';
	labelMapping['famname_z'] = 'Location';
	labelMapping['famname_source'] = 'Source';
		
	labelMapping['corpname_organisation'] = 'Organisation';
	labelMapping['corpname_a'] = 'Organisation';
	labelMapping['corpname_dates'] = 'Dates';
	labelMapping['corpname_y'] = 'Dates';
	labelMapping['corpname_loc'] = 'Location';
	labelMapping['corpname_z'] = 'Location';
	labelMapping['corpname_other'] = 'Other';
	labelMapping['corpname_x'] = 'Other';
	labelMapping['corpname_source'] = 'Source';
	
	labelMapping['geogname_geogname'] = 'Place Name';
	labelMapping['geogname_a'] = 'Place Name';
	labelMapping['geogname_dates'] = 'Dates';
	labelMapping['geogname_y'] = 'Dates';
	labelMapping['geogname_loc'] = 'Location';
	labelMapping['geogname_z'] = 'Location';
	labelMapping['geogname_source'] = 'Source';
	labelMapping['geogname_other'] = 'Other';
	labelMapping['geogname_x'] = 'Other';
	
	labelMapping['title_title'] = 'Title';
	labelMapping['title_a'] = 'Title';
	labelMapping['title_dates'] = 'Dates';
	labelMapping['title_y'] = 'Dates';
	labelMapping['title_source'] = 'Source';

	labelMapping['genreform_a'] = 'Genre';
	labelMapping['genreform_genre'] = 'Genre';
	labelMapping['genreform_source'] = 'Source';

	labelMapping['function_a'] = 'Function';
	labelMapping['function_function'] = 'Function';
	labelMapping['function_source'] = 'Source';



/*adds the selected field to the access point, s is the name of the access point ie. persname */
function addField(s){
	var tableDiv = ($(s + 'table'));
	var table = tableDiv.getElementsByTagName('tbody')[0];
	var dropdownRow = document.getElementById(s + 'dropdown').parentNode.parentNode;
	var value = document.getElementById(s + 'dropdown').value;
	var options = dropdownRow.getElementsByTagName('option');
	var text;
	for (var i=0; i<options.length; i++){
		if (options[i].value == value){
			text = options[i].text;
		}
	}	
	var newRow = document.createElement('tr');
	var cell1 = document.createElement('td');
	var cell2 = document.createElement('td');
	var cell3 = document.createElement('td');
	cell1.innerHTML = '<td class="label">' + text + ': </td>';
	if (value == 'famname_other'){
		cell2.innerHTML = '<input type="text" onfocus="parent.setCurrent(this);" name="' + value + '" id="' + value + '" size="40" value="family"></input>';
	}
	else {
		cell2.innerHTML = '<input type="text" onfocus="parent.setCurrent(this);" name="' + value + '" id="' + value + '" size="40"></input>';
	}
	cell3.innerHTML = '<img src="/ead/img/delete.png" class="deletelogo" onmouseover="this.src=\'/ead/img/delete-hover.png\';" onmouseout="this.src=\'/ead/img/delete.png\';" onclick="deleteRow(this.parentNode.parentNode);" />';
	newRow.appendChild(cell1);
	newRow.appendChild(cell2);
	newRow.appendChild(cell3);
	table.insertBefore(newRow, dropdownRow); 

	var rows = table.getElementsByTagName('tr');
	rows[rows.length-2].getElementsByTagName('input')[0].focus();    
	options[0].selected = true;	
	var tableDnD = new TableDnD();
	tableDnD.init($('table_' + s));
}

function resetAllAccessPoints(){
	var accessPoints = ['subject','persname', 'famname', 'corpname', 'geogname', 'title', 'genreform', 'function'];
	for (var i=0; i< accessPoints.length; i++){
		resetAccessPoint(accessPoints[i]);
	}
}

/*resets the access point back to its original appearance deleting any content, s is the name of the access point ie. persname */
function resetAccessPoint(s){
	var tableDiv = ($(s + 'table'));
	var table = tableDiv.getElementsByTagName('tbody')[0];
	var rows = table.getElementsByTagName('tr');
	if (s == 'language'){
		for (var i=0; i<rows.length; i++){
	  		rows[i].getElementsByTagName('input')[0].value = '';
	  	} 
	}
	else {
		if (s == 'genreform' || s == 'function'){
			for (var i=rows.length-1; i>0; i--){
	    		table.removeChild(rows[i]);
	  		}
		}
		else {
			for (var i=rows.length-2; i>0; i--){
	    		table.removeChild(rows[i]);
	  		}
	  	}
	  	rows[0].getElementsByTagName('input')[0].value = '';
	  	var rules = document.getElementById(s + '_rules');
	  	if (rules != null){
    		rules.options[0].selected=true;   	
      	}
      	checkRules(s);
    }   
}

function addLanguage() {
  /*function to add a language to lang_list after,
  //checking for both lang_code and lang_name*/

  var form = document.getElementById('eadForm');
  var langcode = document.getElementById('lang_code').value;
  var language = document.getElementById('lang_name').value;
  var fields = new Array("lang_code", "lang_name"); 
  
  if (langcode == ""){
    alert("You must enter a 3-letter ISO code for this language.");
  }
  else if (language == ""){
    alert("You must enter a name for this language.");
  } else {
    buildAccessPoint('language');
    resetAccessPoint('language');
  }

}

/* repopulate the access point with the details from the given entry so they can be edited, s is either the name of the access point or the name of the access point
followed by '_formgen' which is used to maintain distinct ids between access points read in from existing xml and those created in the current form,
number is the number which forms part of the unique id */
function editAccessPoint(s, number){
  
	var type = s.substring(0, s.indexOf('_formgen'));
  	if (type == '') {
  		type = s;
  	}  
  	resetAccessPoint(type);
  
  	var string = document.getElementById(s + number + 'xml').value;
  	var values = string.split(' ||| ');
  
 	var tableDiv = ($(type + 'table'));

  	var table = tableDiv.getElementsByTagName('tbody')[0];
  	var rows = table.getElementsByTagName('tr');
  	var inputs = table.getElementsByTagName('input');
  	if (type != 'language' && type != 'genreform' && type != 'function'){
	 	var dropdown = document.getElementById(type + 'dropdown');
  	  	var dropdownRow = dropdown.parentNode.parentNode;
  	}
  	//check to see if the existing access point has either rules or source - one is required - files being edited may not have one 
  	var hasSource = false;
  	var hasRules = false;
	for (var i = 0; i< values.length-1; i++){
	  	if (values[i].split(' | ')[0].split('_', 2)[1] == 'rules'){
  			hasRules = true;
  		}
  		else if (values[i].split(' | ')[0].split('_', 2)[1] == 'source'){
  			hasSource = true;
  		}	
  	}
  	// find all the values in the access point
  	for (var i = 0; i< values.length-1; i++){  
  		value = values[i].split(' | ');
  		if (type == 'language'){
  			inputs[i].value = value[1];
  		}
  		else {
  			//fill in the lead for the access point
		  	if (i == 0){
		  		inputs[i].value = value[1];
		  	}
	  		else {
	  			if (value[0].split('_', 2)[1] == 'rules'){
	  				var rules = document.getElementById(type + '_rules');
					for (var j=0; j<rules.length; j++){
				  		if (rules.options[j].value == value[1]){
				  	 		rules.options[j].selected = true;
				  	 		if (value[1] != 'none'){
				  	 			table.removeChild(rows[1]);
				  	 		}
				  		}
					}
	  			}
	  			else if (value[0].split('_', 2)[0] != 'att') { 			
				  	var newRow = document.createElement('tr');
				  	var cell1 = document.createElement('td');
					var cell2 = document.createElement('td');
					cell1.innerHTML = '<td class="label">' + labelMapping[value[0]] + ': </td>';
					cell2.innerHTML = '<input type="text" onfocus="setCurrent(this);" id="' + value[0] + '" value="' + value[1] + '" size="40"></input>';
					newRow.appendChild(cell1);
					newRow.appendChild(cell2);
					if (value[0].split('_', 2)[1] == 'source'){
						newRow.setAttribute('NoDrag', 'True');
						newRow.setAttribute('NoDrop', 'True');
						table.replaceChild(newRow, rows[1]);
					}
					else {			
						var cell3 = document.createElement('td');
						cell3.innerHTML = '<img src="/ead/img/delete.png" class="deletelogo" onmouseover="this.src=\'/ead/img/delete-hover.png\';" onmouseout="this.src=\'/ead/img/delete.png\';" onclick="deleteRow(this.parentNode.parentNode);" />';
						newRow.appendChild(cell3);		
				  		table.insertBefore(newRow, dropdownRow);			  		
				  	}
			  	}		  	
	  		}
	  	}
  	}
  	//if the current access point does not have rules or source specified then add an empty source box in row 2
  	if (!hasSource && !hasRules && type != 'language'){
	  	var newRow = document.createElement('tr');
		var cell1 = document.createElement('td');
		var cell2 = document.createElement('td');
		cell1.innerHTML = '<td class="label">' + labelMapping[type+'_source'] + ': </td>';
		cell2.innerHTML = '<input type="text" onfocus="setCurrent(this);" id="' + type + '_source" size="40"></input>';
		newRow.appendChild(cell1);
		newRow.appendChild(cell2);
		newRow.setAttribute('NoDrag', 'True');
		newRow.setAttribute('NoDrop', 'True');
		table.replaceChild(newRow, rows[1]);
	}
  	//delete the access point you are now editing
  	deleteAccessPoint(s + number);
  	
  	//initiate drag and drop reordering of cells
  	if (type != 'language' && type != 'genreform' && type != 'function'){
  		var tableDnD = new TableDnD();
  		tableDnD.init($('table_' + type));
  	}
}





/*deletes element with given id */
function deleteAccessPoint(d){
	var div = document.getElementById(d);
  	var xml = document.getElementById(d + 'xml');
  	var br = document.getElementById(d + 'br');  
  	var parent = div.parentNode;
  	parent.removeChild(div);
  	parent.removeChild(xml);
  	parent.removeChild(br);
  	if (parent.getElementsByTagName('div').length < 1){
  		parent.style.display = 'none';
  	} 
}



/* counter initialised for use in addAccessPoint() function*/
var nameCount = 0;

/* adds personal name to the 'addedpersnames' div etc.*/
function addAccessPoint(s){

	if (s == 'persname'){
		var reqfields = new Array("persname_surname");
	}
	else if (s == 'famname'){
	  var reqfields = new Array("famname_surname");
	}
	else if (s == 'corpname'){
	  var reqfields = new Array("corpname_organisation");
	}
	else if (s == 'subject'){
	  var reqfields = new Array("subject_subject");
	}
	else if (s == 'geogname'){
	  var reqfields = new Array("geogname_location");
	}
	else if (s == 'title'){
	  var reqfields = new Array("title_title");
	}
	else if (s == 'genreform'){
	  var reqfields = new Array("genreform_genre");
	}
	else if (s == 'function'){
	  var reqfields = new Array("function_function");
	}
  
  	var fm = document.getElementById('eadForm');
  	//change this to for loop to allow multiple required fields to be set
  	if (fm[reqfields[0]].value == "") {
    	alert("You must give a " + reqfields[0].split('_', 2)[1] + " for this access point.");
  	} 
 	else if (document.getElementById(s + '_source') && document.getElementById(s + '_source').value == ""){
  		alert("You must give a source or specify a rule set for this access point."); 
  	}
  	else {
    	buildAccessPoint(s);
    	resetAccessPoint(s);
  	}
}


/* Build the xml and strings needed for the access point */
function buildAccessPoint(s){
   	var fm = document.getElementById('eadForm');
	var tableDiv = ($(s + 'table'));
    /* retreive all values from section of form and reset form values*/
    var valueString = '';
    var textString = '';  
	var table = tableDiv.getElementsByTagName('tbody')[0];
	var rows = table.getElementsByTagName('tr');
	var length;
	if (s == 'language' || s == 'genreform' || s == 'function'){
		length = rows.length;
	}
	else {
		length = rows.length-1
	}    
    for (var i = 0; i<length; i++){    
    	textbox = rows[i].getElementsByTagName('input')[0]
    	if (textbox.value != ""){
    		if (textbox.id.split('_', 2)[1] == 'source'){
    			valueString +=  textbox.id + ' | ' + textbox.value + ' ||| ';
    			
    		}
    		else {
    			valueString += textbox.id + ' | ' + textbox.value + ' ||| ';
    			textString += textbox.value + ' ';
    		}
    	}   
    }
    var rules = document.getElementById(s + '_rules');
    if (rules != null){
    	valueString += rules.id + ' | ' + rules.value + ' ||| ';
    	rules.options[0].selected=true;
    }
        
    /* add to DOM */
    var div = document.getElementById('added' + s.toLowerCase() + 's');
    var txtnode = document.createTextNode(textString); 
	var number = nameCount;
    nameDiv = document.createElement('div');
    nameDiv.setAttribute('class', 'accesspoint');
    var link = document.createElement('a');    
    link.onclick = function () {editAccessPoint(s, number); },   
    link.setAttribute('title', 'Click to edit');
    link.appendChild(txtnode);
    nameDiv.appendChild(link);
    var icondiv = createIcons(s);

    var wrapper = document.createElement('div');
    wrapper.setAttribute('id', s + nameCount);  
    wrapper.appendChild(icondiv);

    wrapper.appendChild(nameDiv);   
    div.appendChild(wrapper);
    br = document.createElement('br');
    br.setAttribute('id', s + nameCount + 'br');
    div.appendChild(br);
    var hidden = document.createElement('input');
    hidden.setAttribute('type', 'hidden');
    hidden.setAttribute('id', s + nameCount + 'xml'); 
    if (s == 'language'){
    	hidden.setAttribute('name', 'did/langmaterial/' + s);
    }
    else {
    	hidden.setAttribute('name', 'controlaccess/' + s);
    }
    hidden.setAttribute('value', valueString);

    div.appendChild(hidden);
    div.style.display = 'block';

    nameCount++;   	 
}


function createIcons(s){
    var icondiv = document.createElement('div');
    	icondiv.className = 'icons'; 

   /* the delete icon */
   var d = "'" + s + nameCount + "'";
   var s = "'" + s + "'";
   innerHTMLString = '<a onclick ="deleteAccessPoint(' + d + ');" title="delete entry"><img src="/ead/img/delete.png" class="deletelogo" onmouseover="this.src=\'/ead/img/delete-hover.png\';" onmouseout="this.src=\'/ead/img/delete.png\';" id="delete' + nameCount + '"/></a>'; 

   icondiv.innerHTML = innerHTMLString;
   return icondiv
}



/* Function to make sure only source OR rules can be completed for an access point called when a rule is selected from the
drop down box and deletes the source box if present or puts it back if no rule is selected*/
function checkRules(s){
	var rules = ($(s + '_rules'));
	var tableDiv = ($(s + 'table'))
	if (tableDiv == null){
		tableDiv = ($(s.substring(0, s.indexOf('_formgen')) + 'table'));
  	}	
	var table = tableDiv.getElementsByTagName('tbody')[0];
	var rows = table.getElementsByTagName('tr');
	
	if (rules == null){
		if (s == 'subject'){
			var label = 'Thesaurus';
		}
		else {
			var label = 'Source';
		}
		var newRow = document.createElement('tr')
		var cell1 = document.createElement('td');
		var cell2 = document.createElement('td');
		cell1.innerHTML = '<td class="label">' + label + ': </td>';
		cell2.innerHTML = '<input type="text" onfocus="setCurrent(this);" id="' + s + '_source" size="40"></input>';
		newRow.appendChild(cell1);
		newRow.appendChild(cell2);
		newRow.setAttribute('NoDrag', 'True');
		newRow.setAttribute('NoDrop', 'True');
		try {
			table.insertBefore(newRow, rows[1]);
		}
		catch (e){
			table.appendChild(newRow);
		}
	}
	else if (rules.value == 'none'){
		var newRow = document.createElement('tr')
		var cell1 = document.createElement('td');
		var cell2 = document.createElement('td');
		cell1.innerHTML = '<td class="label">Source: </td>';
		cell2.innerHTML = '<input type="text" onfocus="setCurrent(this);" id="' + s + '_source" size="40"></input>';
		newRow.appendChild(cell1);
		newRow.appendChild(cell2);
		newRow.setAttribute('NoDrag', 'True');
		newRow.setAttribute('NoDrop', 'True');
		table.insertBefore(newRow, rows[1]);
		
	}
	else if (rows[1].getElementsByTagName('input')[0].id == s + '_source'){
			table.removeChild(rows[1])		
	}	
}


/* deletes the row from the accesspoint*/
function deleteRow(tr){
	var table = tr.parentNode;
	table.removeChild(tr);
}


