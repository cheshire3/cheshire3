/*
// Program:		form.js
// Version:   	0.01
// Description:
//            	JavaScript functions for the editing form in the Archives Hub editing interface.  
//            	- produced for the Archives Hub v3.x. 
// Language:  	JavaScript
// Author(s):   Catherine Smith <catherine.smith@liv.ac.uk>	
// Date:      	12/01/2009
// Copyright: 	&copy; University of Liverpool 2009
//
// Version History:
// 0.01 - 09/01/2009 - CS- functions completed for first release of Archives Hub editing interface
*/


var recid = 'notSet';
var idExists = null;
var currentForm = 'collectionLevel';
var previousForm = null;
var accessPoints = new Array("subject", "persname", "famname", "corpname", "geogname", "title", "genreform", "function");
var someIdSet = false;
var countryCode = null;
var repositoryCode = null;
var baseUnitId = null;
var fileName = null;
var fileOwner = null;
var timeout;
var daocount = 0;
var required_xpaths_components = new Array('unitid', 'did/unittitle', 'did/unitdate');
var required_xpaths = new Array(
'unitid',
'archoncode',
'countrycode',
'did/unittitle',
'did/unitdate',
'did/unitdate/@normal',
'did/origination',
'did/physdesc/extent',
'scopecontent',
'accessrestrict'
);

function setCountryCode(code){
	if (countryCode == null){
		countryCode = code;
	}
}


function setRepositoryCode(code){
	if (repositoryCode == null){
		repositoryCode = code;
	}
}


function setBaseUnitId(id){
	if (baseUnitId == null){
		baseUnitId = id;
	}
}


function setOwner(owner){
	if (fileOwner == null){
		fileOwner = owner;
	}
}


function setRecid(){
	if (document.getElementById('recid') != null && document.getElementById('recid') != 'notSet'){
		recid = document.getElementById('recid').value;
	}
}


/* basic user operations: submit, delete etc. */

function deleteFromStore(){

	var recid = null;
	if (!document.getElementById('storeDirForm').recid){
		return;
	}
	if (document.getElementById('storeDirForm').recid.length){
		for (var i=0; i < document.getElementById('storeDirForm').recid.length; i++) {
			if (document.getElementById('storeDirForm').recid[i].checked) {
		      	recid = document.getElementById('storeDirForm').recid[i].value;
		    }
		}
	}
	else {
		if (document.getElementById('storeDirForm').recid.checked) {
			recid = document.getElementById('storeDirForm').recid.value;
		}
	}
	
	if (recid == null) {
		return;
	}
	else {
		var ok = confirmOp('You are about to delete ' + recid.substring(0, recid.lastIndexOf('-')) + ' from the editing store. All changes made since it was last submitted to the database will be lost.\nAre you sure you want to continue?')
		if (ok){
			deleteRec(recid);
		}
		else {
			return;
		}
	}
}

function deleteRec(id){
	var url = '/ead/edit/';
	var data = 'operation=deleteRec&recid=' + encodeURIComponent(id);
	var ajax = new Ajax.Request(url, {method:'post', asynchronous:false, postBody:data, evalScripts:true, onSuccess: function(transport) {	
		location.href="/ead/edit/menu.html";		    
	}});		
}

function discardRec(id){
	var url = '/ead/edit/';
	var data = 'operation=discard&recid=' + encodeURIComponent(id);
    if ($('owner') != null){    
    	setOwner($('owner').value);
    }	
	if (fileOwner != null){
		data += '&owner=' + encodeURIComponent(fileOwner);
	}
	var ajax = new Ajax.Request(url, {method:'post', asynchronous:false, postBody:data, evalScripts:true, onSuccess: function(transport) {	
		location.href="/ead/edit/menu.html";		    
	}});		
}


function submit(index){
	if (!checkRequiredData()){
		alert ('the following fields must be entered before proceeding:\n  - Reference Code \n  - Title')
		return;
	}
	if (currentEntryField != null && currentEntryField.value != ''){
    	validateField(currentEntryField, false)
    }
	errors = document.getElementsByClassName('menuFieldError');
    if (errors.length != 0){
    	alert('Please fix the errors in the xml before submitting. Errors will be marked with red shading in the text box.');
    	return;
    }
    //check the daoform details   
	var daodetails = checkDao();
    if (daodetails[0] == true){
 	    var confirmbox = confirm('At least one of File URI values required for the digital object has not been completed. If you proceed with this operation any incomplete URIs will not be included and the title and/or description information relating to the missing URI will be lost. All other content will be saved.\n\nDo you want to continue?');
 		if (confirmbox == false){
 			return;
 		}   			
 		else {			
 			var wipeids = daodetails[1];
 			var descids = daodetails[2];
 			for (var i=0; i< wipeids.length; i++){
 				document.getElementById(wipeids[i]).value = '';
 			}
 			for (var i=0; i< descids.length; i++){
 				document.getElementById(descids[i]).value = '<p></p>';
 			}
 		}
    }
	saveForm(false);
	
	//validate whole record
	invalid = document.getElementsByClassName('invalid');
	if (invalid.length != 0){
		alert('Not all components of your record have the required fields completed. Please complete any components which are coloured red in the contents tree. The missing fields will also be indicated with a red border.');
		return;
	}
	
	url = "?operation=submit&recid=" + encodeURIComponent(recid);
	if (fileOwner != null){
		url += '&owner=' + encodeURIComponent(fileOwner);
	}
	if (fileName != null){
		url += '&filename=' + encodeURIComponent(fileName);
	}
	if (index == false || index == 'false'){
		url += '&index=false';
	}
    location.href= url;
}


function resetForm(){
    if (recid == 'notSet'){
    	var data = 'operation=reset';
    	var loc = $('rightcol');
		new Ajax.Updater(loc, '/ead/edit', {method: 'get', asynchronous:false, parameters:data, evalScripts:true});	
		updateTitle(null);    	
    }
    //if there is a recid (the form has a saved version in the editing store) show the saved version
    else {
    	var form = $('eadForm');
    	var data = 'operation=navigate&recid=' + encodeURIComponent(recid) + '&newForm=' + currentForm; 
    	if (fileOwner != null){
    		data += '&owner=' + encodeURIComponent(fileOwner);
    	}
    	if ($('ctype')){
    		data += '&ctype=' + ($('ctype')).value;
    	}
    	var loc = $('rightcol');
		new Ajax.Updater(loc, '/ead/edit', {method: 'get', asynchronous:false, parameters:data, evalScripts:true});	
		updateTitle(null);
    }
}


function save(){
	var body = document.getElementsByTagName('body')[0];
	body.className = 'waiting';
	//validate and check id existence etc.
    if (!checkRequiredData()){
		alert ('the following fields must be entered before proceeding:\n  - Reference Code \n  - Title');
		body.className = 'none';
		return;
	}
	checkId(false);
	if ($('idError')){
		alert('The form cannot be saved because a file in the database has the same reference code as the record you are creating. Please change the reference code and try again. If you are trying to replace the file in the main database you need to delete it from the database in the admin menu before creating the new file.');
		body.className = 'none';
		return;
	}
	var errors = document.getElementsByClassName('menuFieldError');
    if (errors.length != 0){
    	alert('Please fix the errors in the xml before saving. Errors will be marked with red shading in the text box.');
    	body.className = 'none';
    	return;
    }
    var values = checkEditStore();
    if (values[0] == 'error'){
    	alert('A problem occurred when trying to perform this operation. Please check that the spoke is responding to searches before trying again.');
    	body.className = 'none';
	   	return;
    }
    if (values[0]){
    	if (values[1] == 'user'){
    		var confirmbox = confirm('A file with this Reference code is already in the process of being created or edited. If you proceed with this operation the existing file will be overwritten with this one.\n\nAre you sure you want to continue with this operation?');
 			if (confirmbox == false){
	   			body.className = 'none';
	   			return;
	   		}
   		}
   		else if (values[1] == 'other'){
    		var confirmbox = confirm('A file with this Reference code is already in the process of being created or edited by another user.\n\nAre you sure you want to continue with this operation?');
 			if (confirmbox == false){
	   			body.className = 'none';
	   			return;
	   		}   		
   		}
    }
       
    //check the daoform details   
	var daodetails = checkDao();
    if (daodetails[0] == true){
 	    var confirmbox = confirm('At least one of File URI values required for the digital object has not been completed. If you proceed with this operation any incomplete URIs will not be included and the title and/or description information relating to the missing URI will be lost. All other content will be saved.\n\nDo you want to continue?');
 		if (confirmbox == false){
 			body.className = 'none';
 			return;
 		}   			
 		else {			
 			var wipeids = daodetails[1];
 			var descids = daodetails[2];
 			for (var i=0; i< wipeids.length; i++){
 				document.getElementById(wipeids[i]).value = '';
 			}
 			for (var i=0; i< descids.length; i++){
 				document.getElementById(descids[i]).value = '<p></p>';
 			}
 		}
    }
	findRequiredFields();
	saveForm(false);
	body.className = 'none';
    alert('This form is now saved as ' + recid + ' and can be reloaded from the admin menu for further editing at a later date.');
		
}


function saveForm(asynch){
	var relocate = false;
	resetAllAccessPoints()
	//collect the basic id information
	if (currentForm == 'collectionLevel'){
		setCountryCode($('countrycode').value);
	    setRepositoryCode($('archoncode').value);
	    setBaseUnitId($('unitid').value);
	    if ($('owner') != null){    
	    	setOwner($('owner').value);
	    }
	}
	// if this record has a recid (i.e. is already saved in the editing store) get its recid if we don't have it already
	if (currentForm == 'collectionLevel' && recid=='notSet'){
		if (document.getElementById('recid') != 'notSet'){
	    	recid = document.getElementById('recid').value;
	    }		
	}
	// gets filename if it is set in the form 
	if(currentForm == 'collectionLevel' && fileName == null){
		if (document.getElementById('filename') != null){
			fileName = document.getElementById('filename').value;
		}
	}
  	var data = ($('eadForm')).serialize();
  	data += ('&operation=save&location=' + currentForm);
  	previousForm = currentForm;
  	if (currentForm != 'collectionLevel'){	  			
  		var parent = $(currentForm).parentNode.parentNode.parentNode;	  		
  		if (parent.tagName != 'LI'){
  			var parentId = 'collectionLevel';
  		}
  		else {
  			var linkParent = parent.childNodes[0];
  			parentId = parent.childNodes[1].id;
  		}	  	
  		data += ('&parent=' + parentId);
  	}   
  	else {
  		$('countrycode').readOnly = true;
  		$('archoncode').readOnly = true;
  		$('unitid').readOnly = true;
  	}	
    if (recid != null && recid != 'notSet'){
    	data += '&recid=' + encodeURIComponent(recid);
    }
    else {
    	recid = ($('pui')).value;
    	relocate = true;
    }
    if (fileOwner != null){
    	data += '&owner=' + encodeURIComponent(fileOwner);
    }
    var loc = $('rightcol');
  	var ajax = new Ajax.Request(loc, {method:'post', asynchronous:asynch, postBody:data, evalScripts:true,  onSuccess: function(transport){ 
    	var response = transport.responseText;
	    var rid = response.substring(7,response.indexOf('</recid>'));	
	    var valid = response.substring(response.indexOf('<valid>')+7, response.indexOf('</valid>'));
		if (valid == 'False'){
			($(previousForm)).className = 'invalid';
		}
		else{
			($(previousForm)).className = 'valid';
		}
	}});	
	if (relocate == true){
		window.location.href='/ead/edit/?operation=load&recid=' + encodeURIComponent(recid);
	}
}


function displayForm(id, level, nosave){

	if (nosave == undefined){
		nosave = false;
	}
	/* for adding a new form */
	if (id == 'new'){
		var data = 'operation=add&recid=' + encodeURIComponent(recid) + '&clevel=' + level;
		var loc = $('rightcol');		
	   	new Ajax.Updater(loc, '/ead/edit/', {method: 'post', asynchronous:false, parameters:data, evalScripts:true});

	   	($('countrycode').value) = countryCode;	   			
	   	($('archoncode').value) = repositoryCode;
	   	($('unitid').value) = baseUnitId + '/' + currentForm.replace(/-/g, '/');
	   	($('pui').value) = recid;
	   	updateId();
	}
	/* for navigating to an existing form*/
	else {	 
		if (nosave == false){
			if (!checkRequiredData()){
				alert ('the following fields must be entered before proceeding:\n  - Reference Code \n  - Title');
				return;
			} 	
			errors = document.getElementsByClassName('menuFieldError');
		    if (errors.length != 0){
		    	alert('Please fix the errors in the xml before leaving this page. Errors will be marked with red shading in the text box.');
		    	return;
		    }	
		    //check the daoform details   
			var daodetails = checkDao();
		    if (daodetails[0] == true){
		 	    var confirmbox = confirm('At least one of File URI values required for the digital object has not been completed. If you proceed with this operation any incomplete URIs will not be included and the title and/or description information relating to the missing URI will be lost. All other content will be saved.\n\nDo you want to continue?');
		 		if (confirmbox == false){
		 			return;
		 		}   			
		 		else {			
		 			var wipeids = daodetails[1];
		 			var descids = daodetails[2];
		 			for (var i=0; i< wipeids.length; i++){
		 				document.getElementById(wipeids[i]).value = '';
		 			}
		 			for (var i=0; i< descids.length; i++){
		 				document.getElementById(descids[i]).value = '<p></p>';
		 			}
		 		}
		    }		    
			saveForm(false);
		}	
		var data = 'operation=navigate&recid=' + encodeURIComponent(recid) + '&newForm=' + id;
		if (fileOwner != null){
			data += '&owner=' + encodeURIComponent(fileOwner);
		}
		var loc = $('rightcol');
		new Ajax.Updater(loc, '/ead/edit', {method: 'get', asynchronous:false, parameters:data, evalScripts:true, onSuccess: function(transport){		   	
	    
		}});
		if ($(currentForm)){
			($(currentForm)).style.background = 'none';
		}
	    currentForm = id;
	    ($(currentForm)).style.background = 'yellow';		    		  	 	  	
  	}
  	findRequiredFields();
}


function addComponent(){	
	var body = document.getElementsByTagName('body')[0];
	body.className = 'waiting';
    // check it does not exceed the c12 limit 
    if (currentForm != 'collectionLevel'){
     	var parent = document.getElementById(currentForm);    
      	var listItem = parent.parentNode;
      	var level = Number(listItem.parentNode.getAttribute('name'));
      	if (level == 12){
      		alert('You cannot add any more component levels to this description');
      		body.className = 'none';
      		return;
      	}
    }
   
    //validate and check id existence etc.
    if (!checkRequiredData()){
		alert ('the following fields must be entered before proceeding:\n  - Reference Code \n  - Title')
		body.className = 'none';
		return;
	}
    if (currentEntryField != null && currentEntryField.value != ''){
    	validateField(currentEntryField, false);
    }
    errors = document.getElementsByClassName('menuFieldError');
    if (errors.length != 0){
    	alert('Please fix the errors in the xml before adding a component. Errors will be marked with red shading in the text box.');
    	body.className = 'none';
    	return;
    }  
    else if (currentForm == 'collectionLevel' && recid == 'notSet'){
		var url = '/ead/edit'
		var data = 'operation=checkId&id=' + encodeURIComponent(($('pui')).value) + '&store=recordStore';
		new Ajax.Request(url, {method: 'get', asynchronous: false, parameters: data, onSuccess: function(transport) { 	    				
			var response = transport.responseText;
			var idExists = response.substring(7,response.indexOf('</value>')); 			 
	 	}});
	 	if (idExists == 'true'){
   				alert('A record with this ID already exists in this database\nyou must supply a unique id before proceeding');
   				body.className = 'none';
   				return;
   		}   
	}
	if (currentForm == 'collectionLevel' && recid == 'notSet' && document.getElementById('recid') == 'notSet'){
		var url = '/ead/edit';
		var data = 'operation=checkId&id=' + encodeURIComponent(($('pui')).value) + '&store=editStore';
		new Ajax.Request(url, {method: 'get', asynchronous: false, parameters: data, onSuccess: function(transport) { 	    				
			var response = transport.responseText;
			var idExists = response.substring(7,response.indexOf('</value>'));
   			if (idExists == 'true'){
   				var cont = confirmOp('A record with this ID already exists within the editing store which means it has either been loaded for editing or is in the process of being created by you or another user and has not yet been submitted to the main database. If you continue you will overwrite this record and it will be lost \n\n Are you sure you want to continue? ');
   				if (!cont){
					body.className = 'none';
					return;
				} 	
   			}     			
	 	}});
	}  
	
    //check the daoform details   
	var daodetails = checkDao();
    if (daodetails[0] == true){
 	    var confirmbox = confirm('At least one of File URI values required for the digital object has not been completed. If you proceed with this operation any incomplete URIs will not be included and the title and/or description information relating to the missing URI will be lost. All other content will be saved.\n\nDo you want to continue?');
 		if (confirmbox == false){
 			body.className = 'none';
 			return;
 		}   			
 		else {			
 			var wipeids = daodetails[1];
 			var descids = daodetails[2];
 			for (var i=0; i< wipeids.length; i++){
 				document.getElementById(wipeids[i]).value = '';
 			}
 			for (var i=0; i< descids.length; i++){
 				document.getElementById(descids[i]).value = '<p></p>';
 			}
 		}
    }
	//update the menu bar first
    if (currentForm == 'collectionLevel'){	    	
      	var parent = document.getElementById('collectionLevel');
      	var level = 0;
      	var listItem = document.getElementById('treeDiv');
    } 
    else {  
      	var parent = document.getElementById(currentForm);    
      	var listItem = parent.parentNode;
      	var level = Number(listItem.parentNode.getAttribute('name'));
    }
	parent.style.background = 'none';

    
    // find the right list or add a new one
    var childList = null;  
    childList = listItem.childNodes;
    var list = null;
    if (childList != null){
      	for(var i=0; i<childList.length; i++){
        	if (childList[i].tagName == 'UL'){
          		list = childList[i];
        	}
      	}
    }
    if (list == null){
      	list = document.createElement('ul');
      	list.setAttribute('name', (level + 1));
      	list.className =  'hierarchy';
      	if (someIdSet == false){
      		if (document.getElementById('someId')){
      			someIdSet = true;
      		}
      		else {
      			list.setAttribute('id', 'someId');
      			someIdSet = true;
      		}
      	}
      	listItem.appendChild(list);
      	//if this element isn't collection level remove the delete option since it now isn't a leaf node
		if (currentForm != 'collectionLevel'){
			var del = null
			if (del = document.getElementById('delete_' + currentForm)){
				del.parentNode.removeChild(del);
			}
		}
    }  

    // create the linkId
    var linkId = '';    
      
    var parentLoc = '';
    if (level > 0){
      	var parentId = parent.getAttribute('id');
      	var parentLoc = parentId;
      	if (parentLoc != undefined){
        	linkId += (parentLoc + '-');
      	}	
    }

    var elementCount = list.childNodes.length;
    if (elementCount != undefined){
    	if (elementCount == 0){
    		linkId += 1;
    	}
    	else {
    		var previousNode;
    		if (previousNode = list.childNodes[elementCount-1].childNodes[1]){
	    		var previousId = previousNode.getAttribute('id');
	    		var number = Number(previousId.substring(previousId.lastIndexOf('-')+1)); 		
	    		linkId += number + 1;	
	    	}	
	    	else {
	    		linkId += '1';
	    	}
    	}    	
    }

	// create the html
    var newItem = document.createElement('li');

    var newLink = document.createElement('a');
    newLink.style.display = 'inline';
    newLink.setAttribute('id', linkId);
  	newLink.style.background = 'yellow';
    newLink.setAttribute('name', 'link');
    newLink.onclick = new Function("javascript: displayForm(this.id, 0)");
    newLink.className = 'invalid';
    newLink.appendChild(document.createTextNode(linkId));
    
    deleteLink = document.createElement('a');
    deleteLink.setAttribute('id', 'delete_' + linkId);
    deleteLink.onclick = new Function("javascript: deleteComponent('" + linkId + "')");

    deleteImage = document.createElement('img');
    deleteImage.setAttribute('src', '/ead/img/delete.png');
    deleteImage.setAttribute('onmouseover', 'this.src=\'/ead/img/delete-hover.png\';')
    deleteImage.setAttribute('onmouseout', 'this.src=\'/ead/img/delete.png\';')
    deleteImage.className = 'deletelogo';
    
    deleteLink.appendChild(deleteImage);
        
    newItem.appendChild(newLink);
    newItem.appendChild(deleteLink);

    list.appendChild(newItem);
    

	refreshTree('someId');
	
	//save the current form and display the new one
	saveForm(true);
	currentForm = linkId;
	setCurrent('none'); //used by character keyboard to display current field - when swap forms need to set to none
	displayForm('new', level + 1);
	body.className = 'none';
}


function deleteComponent(id){
	var body = document.getElementsByTagName('body')[0];
	body.className = 'waiting';
	var link = document.getElementById(id);	
	var compid = link.innerHTML;
	
	var confirmbox = confirm('This operation will permanently delete the component "' + compid + '"\n\n Are you sure you want to continue?');
	if (confirmbox == false){
		body.className = 'none';
		return;
	}
	
	var data = 'operation=delete&recid=' + encodeURIComponent(recid) + '&id=' + id;
	if (fileOwner != null){
    	data += '&owner=' + encodeURIComponent(fileOwner);
    }
	var url = '/ead/edit';
	var value = 'false';
	new Ajax.Request(url, {method: 'get', asynchronous: false, parameters: data, onSuccess: function(transport) { 	    				
		var response = transport.responseText;
		value = response.substring(7,response.indexOf('</value>'));			   					
	}});
	if (value == 'false'){
		alert('There was an error while deleting the component. Please reload the file and try again');
	}
	else{
		//delete from tree
		var listItem = link.parentNode;
		var ul = listItem.parentNode;
		ul.removeChild(listItem);
		if (ul.childNodes.length == 0){
			grandparent = ul.parentNode
			grandparent.removeChild(ul);
			if (id.length > 1){
				grandparentId = id.substring(0, id.lastIndexOf('-')).substring(0, id.lastIndexOf('-'));
				deleteLink = document.createElement('a');
			    deleteLink.setAttribute('id', 'delete_' + grandparentId);
			    deleteLink.onclick = new Function("javascript: deleteComponent('" + grandparentId + "')");
			
			    deleteImage = document.createElement('img');
			    deleteImage.setAttribute('src', '/ead/img/delete.png');
			    deleteImage.setAttribute('onmouseover', 'this.src=\'/ead/img/delete-hover.png\';')
    			deleteImage.setAttribute('onmouseout', 'this.src=\'/ead/img/delete.png\';')
			    deleteImage.className = 'deletelogo';
			    
			    deleteLink.appendChild(deleteImage);
			    
			    grandparent.appendChild(deleteLink);
			}
		}
		//if current form has just been deleted display parent form
		if (id == currentForm){
			if (id.indexOf('-') == -1){
				displayForm('collectionLevel', '0', true);
			}
			else {
				displayForm(id.substring(0, id.lastIndexOf('-')), '0', true);
			}
		}
	}
	refreshTree('someId');
	body.className = 'none';
}

function viewXml(){
	if (!checkRequiredData()){
		alert ('the following fields must be entered before proceeding:\n  - Reference Code \n  - Title');
		return;
	}
	if (currentEntryField != null && currentEntryField.value != ''){
    	validateField(currentEntryField, false);
    }
    errors = document.getElementsByClassName('menuFieldError');
    if (errors.length != 0){
    	alert('Please fix the errors in the xml before viewing. Errors will be marked with red shading in the text box.');
    	return;
    } 
    //check the daoform details   
	var daodetails = checkDao();
    if (daodetails[0] == true){
 	    var confirmbox = confirm('At least one of File URI values required for the digital object has not been completed. If you proceed with this operation any incomplete URIs will not be included and the title and/or description information relating to the missing URI will be lost. All other content will be saved.\n\nDo you want to continue?');
 		if (confirmbox == false){
 			return;
 		}   			
 		else {			
 			var wipeids = daodetails[1];
 			var descids = daodetails[2];
 			for (var i=0; i< wipeids.length; i++){
 				document.getElementById(wipeids[i]).value = '';
 			}
 			for (var i=0; i< descids.length; i++){
 				document.getElementById(descids[i]).value = '<p></p>';
 			}
 		}
    }
	saveForm(false);
	var url = '/ead/edit?operation=xml&recid=' + encodeURIComponent(recid);
	if (fileOwner != null){
		url += '&owner=' + encodeURIComponent(fileOwner);
	}
	window.location.href=url;
}


function previewRec(){
	if (!checkRequiredData()){
		alert ('the following fields must be entered before proceeding:\n  - Reference Code \n  - Title')
		return;
	}
	if (currentEntryField != null && currentEntryField.value != ''){
    	validateField(currentEntryField, false);
    }
    errors = document.getElementsByClassName('menuFieldError');
    if (errors.length != 0){
    	alert('Please fix the errors in the xml before viewing. Errors will be marked with red shading in the text box.');
    	return;
    } 
    //check the daoform details   
	var daodetails = checkDao();
    if (daodetails[0] == true){
 	    var confirmbox = confirm('At least one of File URI values required for the digital object has not been completed. If you proceed with this operation any incomplete URIs will not be included and the title and/or description information relating to the missing URI will be lost. All other content will be saved.\n\nDo you want to continue?');
 		if (confirmbox == false){
 			return;
 		}   			
 		else {			
 			var wipeids = daodetails[1];
 			var descids = daodetails[2];
 			for (var i=0; i< wipeids.length; i++){
 				document.getElementById(wipeids[i]).value = '';
 			}
 			for (var i=0; i< descids.length; i++){
 				document.getElementById(descids[i]).value = '<p></p>';
 			}
 		}
    }
	saveForm(false);
	url = '/ead/edit?operation=preview&recid=' + encodeURIComponent(recid);	
	if (fileOwner != null){
		url += '&owner=' + encodeURIComponent(fileOwner);
	}
	window.location.href=url;
}
	


/* */


function reassignToUser(){
	var recid = null;
	var ok = false;
	if (!document.getElementById('storeDirForm').recid){
		return;
	}
	var user = document.getElementById('storeDirForm').user.value;
	if (document.getElementById('storeDirForm').recid.length){
		for (var i=0; i < document.getElementById('storeDirForm').recid.length; i++) {
			if (document.getElementById('storeDirForm').recid[i].checked) {
		      	recid = document.getElementById('storeDirForm').recid[i].value;
		    }
		}
	}
	else {
		if (document.getElementById('storeDirForm').recid.checked) {
			recid = document.getElementById('storeDirForm').recid.value;
		}
	}
	if (user != 'null' && recid != null){
		var conflict = conflicts(recid.substring(0, recid.lastIndexOf('-')+1)+user);
		if (conflict){
			ok = confirmOp(user + ' already has this file in the editing process. Continuing with this operation will result in ' + user + '\'s current version being lost.\n Are you sure you want to continue to assign this file to ' + user + '?')
		}
		if (ok || !conflict){
			var url = '/ead/edit/';
			var data = 'operation=reassign&recid=' + encodeURIComponent(recid) + '&user=' + encodeURIComponent(user);
			var ajax = new Ajax.Request(url, {method:'post', asynchronous:false, postBody:data, evalScripts:true, onSuccess: function(transport) {  	
				location.href="/ead/edit/menu.html";		    
			}});
		}	
	}
}



function addElement(s){
	$(s).toggle();
  	if ($(s).visible($(s))){
  		$(('link' + s)).update('hide content');		
  	}
 	else {
 		if (s == 'daooptnsdiv'){
 			$(('link' + s)).update('add content');
 		}
 		else {
	 		var value = $(s).getValue($(s)).strip();
		 	if (value == '' || value == ' ' || value == '<p></p>' || value.replace(/[\s]+/g, ' ') == '<p> </p>'){
				$(('link' + s)).update('add content');	
		  	} 
		  	else { 
				$(('link' + s)).update('show content');
		  	}
		}
	}
}



//================================================================================================
// passive UI Functions to update left hand column navigation menu

function updateTitle(field) {
  	var link = document.getElementById(currentForm);
  	var title = ($('did/unittitle')).value;
  	if (title.indexOf('<') != -1){
		title = title.replace(/<\/?\S+?>/g, '');
  	}
  	var id = $('unitid').value;
  	if(field){
  		validateField(field);
  	}
  	if (title == '' && id == ''){
  		//link.update(currentForm);
  		link.innerHTML = currentForm;
  	}
  	else {
    	//link.update(id + ' - ' + title);
    	link.innerHTML = id + ' - ' + title;
	}
}


function updateId() {
  	var link = document.getElementById(currentForm);
  	var title = ($('did/unittitle')).value;
  	if (title.indexOf('<') != -1){
		title = title.replace(/<\/?\S+?>/g, '');
  	}
  	var countryCode = $('countrycode').value.toLowerCase();
  	var repositoryCode = $('archoncode').value;
  	var id = $('unitid').value;
  	
  	if (title == '' && id == ''){
  		link.innerHTML = currentForm;
  	}
  	else {
    	link.innerHTML = id + ' - ' + title;
	}
	var match = true;
	if (currentForm == 'collectionLevel'){ 
		if (($('pui')).getAttribute('disabled') == null || ($('pui')).getAttribute('disabled') == false){
			lowerCaseId = '';
			for (var i=0; i<id.length; i++){
				if (id.charAt(i) != ' '){
					lowerCaseId += id.charAt(i).toLowerCase();
				}
			}
			for (var i=0; i < countryCode.length; i++){
				if (countryCode.charAt(i) != lowerCaseId.charAt(i)){
					match = false;
				}
			}
			lowerCaseId = lowerCaseId.replace(' ', '').replace('/', '-').replace('\\', '-').replace('\'', '');
			if (match == true){
				for (var i=0; i < repositoryCode.length; i++){
					if (repositoryCode.charAt(i) != lowerCaseId.charAt(i+2)){
						match = false;
					}
				}
				if (match == true){
					($('pui')).value = lowerCaseId;
				}
				else {
					($('pui')).value = countryCode + repositoryCode + lowerCaseId;
				}
			}
			else {
				($('pui')).value = countryCode + repositoryCode + lowerCaseId;
			}
		}	
	}
}


//================================================================================================
//validation related functions


function findRequiredFields(){
	if (currentForm == 'collectionLevel'){
		var reqList = required_xpaths;
		//check there is a language
		var lang = document.getElementById('lang_name');
		var langcode = document.getElementById('lang_code');
		if (document.getElementById('addedlanguages').style.display == 'none'){
			lang.style.borderColor = 'red';
			langcode.style.borderColor = 'red';
		}
		else {
			lang.style.borderColor = 'white';
			langcode.style.borderColor = 'white';			
		}
	}
	else {
		var reqList = required_xpaths_components;		
	}
	for (var i=0; i<reqList.length; i++){
		if (document.getElementById(reqList[i])){
			var elem = document.getElementById(reqList[i]);
			value = elem.value.strip();
			if (value == '' || value == ' ' || value == '<p></p>' || value.replace(/[\s]+/g, '') == '<p> </p>'){	
				elem.style.borderColor = 'red';
			
			}
			else {	
				elem.style.borderColor = 'white';
			}
		}
		else if (document.getElementById(reqList[i] + '[1]')){
			var elem = document.getElementById(reqList[i] + '[1]');
			value = elem.value.strip();
			if (value == '' || value == ' ' || value == '<p></p>' || value.replace(/[\s]+/g, '') == '<p> </p>'){
				elem.style.borderColor = 'red';	
			}		
			else {
				elem.style.borderColor = 'white';
			}
		}
	}	
}

function checkDao(){
    var daodiv = document.getElementById('daocontainer');
    var divs = daodiv.getElementsByTagName('div');
    var daoerror = false;
    var descids = [];   
    var wipeids = [];
    for (var i=0; i<divs.length; i++){
    	if (divs[i].className == 'embed' || divs[i].className == 'new'){
    		var inputs = divs[i].getElementsByTagName('input');
    		var href = '';
    		var desc = '';
    		var descid;
    		for (var j=0; j<inputs.length; j++){
    			if (inputs[j].name.search(/href/) != -1){
    				href = inputs[j].value;
    			}
    			else if (inputs[j].name.search(/desc/) != -1){
    				desc = inputs[j].value;
					descid = inputs[j].id;
    			}
    		}
    		if (href.strip() == '' && (desc.strip() != '' && desc.strip() != '<p></p>' && desc.strip().replace('/[\s]+/g', ' ') != '<p> </p>')){
    			descids[descids.length] = descid;
				daoerror = true;
    		}   		
    	} else if (divs[i].className == 'thumb'){
    		var inputs = divs[i].getElementsByTagName('input');
    		var href1 = '';
    		var href2 = '';
    		var desc = '';	
    		var descid = '';
    		for (var j=0; j<inputs.length; j++){
    			if (inputs[j].name.search(/href1/) != -1){
    				href1 = inputs[j].value;
    				href1id = inputs[j].id;
    			}
    			if (inputs[j].name.search(/href2/) != -1){
    				href2 = inputs[j].value;
    				href2id = inputs[j].id;
    			}
    			else if (inputs[j].name.search(/desc/) != -1){
    				desc = inputs[j].value;
					descid = inputs[j].id;
    			}
    		}	
    		if (href1.strip() == '' || href2.strip() == ''){
    			if (href1.strip() != '' || href2.strip() != '' || (desc.strip() != '' && desc.strip() != '<p></p>' && desc.strip().replace('/[\s]+/g', ' ') != '<p> </p>')){
	    			wipeids[wipeids.length] = href1id;
	    			wipeids[wipeids.length] = href2id;
	    			descids[descids.length] = descid;
					daoerror = true;
	    		}
    		}
    	} else if (divs[i].className == 'multiple'){
    		var inputs = divs[i].getElementsByTagName('input');
    		var length = inputs.length;
    		var total = (length-2)/3;
    		var problems = false;
    		var list = new Array();
    		var pairs = new Array(); 		
    		var ids = new Array();
    		for (var j=0; j < total; j++){
    			pairs[j] = [];
    			ids[j] = [];
    		}
    		var desc = '';
    		var descid = '';	
    		for (var j=0; j<length-1; j++){
				var name = inputs[j].name;
				if (name.search(/desc/) != -1){
					desc = inputs[j].value;
					descid = inputs[j].id;
				}
				else {
					var number = (name.split('|')[1].match(/\d+/))-1;
					if (inputs[j].name.search(/href/) != -1){
						pairs[number][0] = inputs[j].value;
						ids[number][0] = inputs[j].id;
					}
					if (inputs[j].name.search(/title/) != -1){
						pairs[number][1] = inputs[j].value;
						ids[number][1] = inputs[j].id;
					}
				}
    		}
    		var wipecount = 0;
    		for (var j=0; j<pairs.length; j++){
    			if (pairs[j].length > 0 && pairs[j][0].strip() == ''){
    				wipecount++;
    				if (pairs[j][1].strip() != ''){  				
	    				wipeids[wipeids.length] = ids[j][0];
	    				wipeids[wipeids.length] = ids[j][1];
	    				problems = true;
	    			}  				
    			}
    		}  
    		if (wipecount == total){
 				descids[descids.length] = descid;
 			} 		
			if (problems == false){
				if ((desc.strip() != '' || desc.strip() != '<p></p>' || desc.strip().replace(/[\s]+/g, ' ') != '<p> </p>')){
					var entries = false;
					for (var j = 0; j < pairs.length; j++){
						if (pairs[j].length > 0 && pairs[j][0].strip() != ''){
							entries = true;
						}
					}
					if (entries == false){	
						descids[descids.length] = descid;
						problems = true;
					}
				}
			}
			if (problems == true){				
    			daoerror = true;
    			
   			}    		   		
    	}
    }
    return [daoerror, wipeids, descids];

}

function conflicts(recid){
	var conflict = null;
	var error = false;
	if (recid != null){
		
		var url = '/ead/edit'
		var data = 'operation=checkId&id=' + encodeURIComponent(recid) + '&store=editStore';
		new Ajax.Request(url, {method: 'get', asynchronous: false, parameters: data, onSuccess: function(transport) { 
			if (response.substring(0, 4) == "<!--"){
				error = true;
			}
			var response = transport.responseText;
			conflict = response.substring(7,response.indexOf('</value>'));
		}});
	}
	else {
		return false;
	}
	if (error == true){
		alert('A problem occurred when trying to perform this operation. Please check that the spoke is responding to searches before trying again.');
	}
	else {
		if (conflict == 'true'){
			return true;
		}
		else {
			return false;
		}
	}
}


/*function checkRecordStoreConficts(form){
	var filepath = null;
	for (var i=0; i < document.getElementById(form).filepath.length; i++) {
		if (document.getElementById(form).filepath[i].checked) {
	      	filepath = document.getElementById(form).filepath[i].value;
	    }
	}
	if (filepath == null && document.getElementById(form).filepath){
		if (document.getElementById(form).filepath.checked) {
	      	filepath = document.getElementById(form).filepath.value;
	    }
	}
	if (filepath == null){
		filepath = document.getElementById('localEdit').value;
	}	
	if (filepath != null){
	 	var conflict = 'false';
		var url = '/ead/edit'
		var data = 'operation=getCheckRecStoreId&filepath=' + filepath;
		new Ajax.Request(url, {method: 'post', asynchronous: false, parameters: data, onSuccess: function(transport) { 
			var response = transport.responseText;	
			if (response.substring(0, 4) == "<!--"){
				alert('A problem occurred when trying to perform this operation. Please check that the spoke is responding to searches before trying again.');
				return;
			}
			conflict = response.substring(response.indexOf('<value>')+7, response.indexOf('</value>'));
		}});
		if (conflict == 'false'){
			checkEditStoreConflicts(form);
		}
		else {
			alert('A file with the same ID as the file you are trying to upload already exists in your spokes database. In order to edit this file you must import it from the spoke database rather than uploading from your local file store.');
			return;	
		}
	}	
}*/


function checkEditStoreConflicts(form){
	var filepath = null;
	for (var i=0; i < document.getElementById(form).filepath.length; i++) {
		if (document.getElementById(form).filepath[i].checked) {
	      	filepath = document.getElementById(form).filepath[i].value;
	    }
	}
	if (filepath == null && document.getElementById(form).filepath){
		if (document.getElementById(form).filepath.checked) {
	      	filepath = document.getElementById(form).filepath.value;
	    }
	}
	if (filepath == null){
		filepath = document.getElementById('localEdit').value;
	}
	if (filepath != null){
	    var conflict = 'false';
	    var overwrite = 'false';
	    var error = false;
	    var users = null;
		var url = '/ead/edit'
		var data = 'operation=getCheckId&filepath=' + filepath;
		new Ajax.Request(url, {method: 'get', asynchronous: false, parameters: data, onSuccess: function(transport) { 
			var response = transport.responseText;
			if (response.substring(0, 4) == "<!--"){
				error = true;
			}			
			conflict = response.substring(response.indexOf('<value>')+7, response.indexOf('</value>'));
			if (response.indexOf('<overwrite>') > -1){
				overwrite = response.substring(response.indexOf('<overwrite>')+11, response.indexOf('</overwrite>'));
			}
			if (response.indexOf('<id>') > -1){
				id = response.substring(response.indexOf('<id>')+4, response.indexOf('</id>'));
			}
			if (response.indexOf('<users>') > -1){
				users = response.substring(response.indexOf('<users>')+7, response.indexOf('</users>'));
			}
		}});
		if (error == true){
			alert('A problem occurred when trying to perform this operation. Please check that the spoke is responding to searches before trying again.');
			return;	
		}
		if (conflict == 'false'){
			document.getElementById(form).submit();
		}
		else if (overwrite == 'true'){
			alert('You already have this file open for editing as ' + id + '. Please delete the file currently in the Draft File Store before reloading');
			return;			
		}
		else if (users != null){
			var ok = confirmOp('The following users already have this file open for editing\n\n ' + users + '\n\n Are you sure you want to continue?');
			if (ok){
				document.getElementById(form).submit();
			}
			else {
				return;
			}
		}
	}
	else {
		return;
	}	
}



function validateFieldDelay(field, asynch){
	clearTimeout(timeout);
	timeout = setTimeout(function() {validateXML(field, asynch)}, 2000);
}

function validateField(field, asynch){
	clearTimeout(timeout);
	validateXML(field, asynch);
}


function validateXML(field, asynch){
	var url = '/ead/edit/';
	var data = 'operation=validate&text=' + field.value.replace('%', '%25');
	
	var ajax = new Ajax.Request(url, {method: 'get', asynchronous: asynch, parameters: data, onSuccess: function(transport) { 		
		var response = transport.responseText;
		var valid = response.substring(7,response.indexOf('</value>'));
		if (valid == 'false'){
			field.className = 'menuFieldError';
		}
		else {
			field.className = 'menuField';
		}	    					    		     
	}});
}

function checkEditStore(){
	var value = false;
	var owner = '';
	var error = false;
	if (currentForm == 'collectionLevel'){		
		if (recid == null || recid == 'notSet'){
			if ($('countrycode').value != ''){
				if ($('archoncode').value != ''){
					if ($('unitid').value != ''){
						var id = $('countrycode').value.toLowerCase() + $('archoncode').value + $('unitid').value.replace(' ', '').replace('/', '-').replace('\\', '-').replace('\'', '').toLowerCase();
						var url = '/ead/edit'
						var data = 'operation=checkEditId&id=' + encodeURIComponent(id);
						new Ajax.Request(url, {method: 'get', asynchronous: false, parameters: data, onSuccess: function(transport) { 	    				
						    var response = transport.responseText;
						    if (response.substring(0, 4) == "<!--"){
								error = true;
							}						    					
						    idExists = response.substring(response.indexOf('<value>')+7, response.indexOf('</value>'));	
						    if (idExists == 'true'){
						    	value = true;
						    	owner = response.substring(response.indexOf('<owner>')+7, response.indexOf('</owner>'));			    
						    }	
							
			 			}});
					} 
				} 
			} 
		} 
	}
	if (error == true){
		return ['error'];
	}
	else {
		var values = [value, owner];
		return values;
	}
}


// NEED TO ADD ERROR CATCH HERE
function checkId(asynch){
	if (recid == null || recid == 'notSet'){
		if ($('countrycode').value != ''){
			if ($('archoncode').value != ''){
				if ($('unitid').value != ''){
					var id = $('countrycode').value.toLowerCase() + $('archoncode').value + $('unitid').value.replace(' ', '').replace('/', '-').replace('\\', '-').replace('\'', '').toLowerCase();
					var url = '/ead/edit'
					var data = 'operation=checkId&id=' + encodeURIComponent(id) + '&store=recordStore';
					new Ajax.Request(url, {method: 'get', asynchronous: asynch, parameters: data, onSuccess: function(transport) { 	    				
					    var response = transport.responseText;
					    var idExists = response.substring(7,response.indexOf('</value>'));					    
					    if (idExists == 'true' && !($('idError'))){
					    	var element = document.createElement('p');
					    	element.className = 'error';
					    	element.setAttribute('id', 'idError');
					    	element.appendChild(document.createTextNode('Reference code already exists in database'));
					    	($('unitidparent')).appendChild(element);
					    }
					    else {
					    	if (idExists == 'false' && ($('idError'))){
					    		($('unitidparent')).removeChild($('idError'));
					    	}
					    }	
						
		 			}});
				}
			}
		}
	}	
	updateId();
}


function checkRequiredData(){
	if ($('did/unittitle').value == ''){
		return false;
	}
	else if ($('unitid').value == ''){
		return false;
	}
	else if ($('archoncode').value == '' && currentForm == 'collectionLevel'){
		return false;
	}
	else if ($('countrycode').value == '' && currentForm == 'collectionLevel'){
		return false;
	}	
	else {
		return true;
	}
}


//================================================================================================
//keyboard related functions

var currentCharTable = 'lower';

function toggleKeyboard(){
  	var keyboard = ($('keyboard')); 
  	keyboard.toggle();  
  	showCharTable('lower');
}


function showCharTable(type){
	if (type == 'lower'){
  		($('chartablelower')).style.display = 'block';
  		($('chartableupper')).style.display = 'none';
  	}
  	else if (type == 'upper'){
  		($('chartableupper')).style.display = 'block';
  		($('chartablelower')).style.display = 'none';   	
  	}
  	else {
		($('chartable' + currentCharTable)).style.display = 'block';
  	}
  	($('hideicon')).style.display = 'inline';
  	($('showicon')).style.display = 'none';
}


function hideCharTable(){
	if (($('chartableupper')).style.display == 'block'){
		currentCharTable = 'upper';
	}
	else {
		currentCharTable = 'lower';
	}
  	($('chartableupper')).style.display = 'none';
  	($('chartablelower')).style.display = 'none';
  	
  	($('showicon')).style.display = 'inline';
  	($('hideicon')).style.display = 'none';
}


//====================================================================================================
//context menu related functions 
function hideAllMenus(){
	document.getElementById('tagmenu').style.display = 'none';
	hideSubMenus();
}


function showSubMenu(type, pos, parent){
	if (parent == 'tagmenu'){
		hideSubMenus();
	}
	var menu = null;
	
	menu = ($(type + 'menu'));

	mainMenu = document.getElementById(parent);
	size = mainMenu.getElementsByTagName('LI');
	menu.style.top = parseInt(mainMenu.style.top) + ((mainMenu.offsetHeight / size.length) * pos) + 'px';
	var width = document.getElementById('content').offsetWidth;
	// if we don't have enough space on the right
	if (parseInt(mainMenu.style.left) + (mainMenu.offsetWidth * 2) > width){
		menu.style.left = parseInt(mainMenu.style.left) - (mainMenu.offsetWidth)  + 'px';
	}
	//if we do have enough space on the right
	else {
		menu.style.left = parseInt(mainMenu.style.left) + (mainMenu.offsetWidth) + 'px';
	}
	menu.style.display = 'block';
}


function hideSubMenus(){
	($('linkmenu')).style.display = 'none';
	($('titlemenu')).style.display = 'none';
	($('listmenu')).style.display = 'none';
	($('fontmenu')).style.display = 'none';
	($('archivalmenu')).style.display = 'none';
}

function hideSubMenu(type){
	($(type + 'menu')).style.display = 'none';
}

/*
// Description: a function to tag selected text in a specified field (text, textarea)
// Author:    John Harrison <johnpaulharrison@googlemail.com>
// Copyright &copy; John Harrison 2006
// Date:      04 January 2006
*/
function addTag(tagtype) {
	var field = currentEntryField;
	var scrollPos = field.scrollTop;
	if (tagtype == 'list'){
		var startTag = '<list><item>'
		var endTag = '</item></list>'
	}
	else if (tagtype == 'comment'){
		var startTag = '<!-- '
		var endTag = ' -->'
	}
	else {
		var startTag = '<' + tagtype + '>'
		var endTag = '</' + tagtype.split(' ', 2)[0] + '>'
	}
	if (field.selectionStart || field.selectionStart == '0') {
		// Firefox 1.0.7, 1.5.0 - tested
		var startPos = field.selectionStart;
		var endPos = field.selectionEnd;
		if (endPos < startPos)	{
			var temp = end_selection;
			end_selection = start_selection;
			start_selection = temp;
		}
		var selected = field.value.substring(startPos, endPos);
		field.value = field.value.substring(0, startPos) + startTag + selected + endTag + field.value.substring(endPos, field.value.length);
	}
	else if (document.selection) {
		//Windows IE 5,6 - tested
		field.focus();
		selection = document.selection.createRange();
		var seltext = selection.text;
		selection.text = startTag + seltext + endTag;
	}
	else if (window.getSelection) {
		// Mozilla 1.7, Safari 1.3 - untested
		selection = window.getSelection();
		var seltext = selection.text;
		selection.text = startTag + seltext + endTag;
	}
	else if (document.getSelection) {
		// Mac IE 5.2, Opera 8, Netscape 4, iCab 2.9.8 - untested
		selection = document.getSelection();
		var seltext = selection.text;
		selection.text = startTag + seltext + endTag;
	} 
	else field.value += startTag + endTag;
	if (scrollPos){
		field.scrollTop = scrollPos;
	}
}

/*
DAO related stuff
*/

function addFile(id){
	var doform = document.getElementById(id);
	var tbody = doform.getElementsByTagName('tbody')[0];
	var rowList = tbody.getElementsByTagName('tr');	
	var rows = rowList.length;	
	var jsrow = rowList[rows-2];
	
	nextfile = ((rows - 2)/2) + 1
	
	if (nextfile%2 == 0){
		var shading = 'odd';
	}
	else{
		var shading = 'even';
	}
		
//file uri
 	var tr = document.createElement('tr');
 	tr.className = shading;
 	var td = document.createElement('td');
 	td.appendChild(document.createTextNode('File ' + nextfile + ' URI: '));
 	td.className = 'label';
 	tr.appendChild(td);
  				
 	href = document.createElement('input');
 	href.setAttribute('type', 'text');
 	href.onclick = function () {setCurrent(this); },
 	href.setAttribute('name', 'dao' + daocount + '|href' + nextfile);
 	href.setAttribute('id', 'dao' + daocount + '|href' + nextfile);
 	href.setAttribute('size', '70');
 	td = document.createElement('td');		
 	td.appendChild(href);
 			
 	tr.appendChild(td);
  
 	tbody.insertBefore(tr, jsrow);   	


//file title   			
	tr = document.createElement('tr');
	tr.className = shading;
	td = document.createElement('td');
	td.appendChild(document.createTextNode('File ' + nextfile + ' title: '));
	td.className = 'label';
	tr.appendChild(td);
	
	href = document.createElement('input');
	href.setAttribute('type', 'text');
	href.onclick = function () {setCurrent(this); },
	href.setAttribute('name', 'dao' + daocount + '|title' + nextfile);
	href.setAttribute('id', 'dao' + daocount + '|title' + nextfile);
	href.setAttribute('size', '70');
	td = document.createElement('td');		
	td.appendChild(href);
	
	tr.appendChild(td);
	
	tbody.insertBefore(tr, jsrow);      			
   			 
 //role info
    role = document.createElement('input');
   	role.setAttribute('type', 'hidden');
   	role.setAttribute('name', 'dao' + daocount + '|role' + nextfile);
   	role.setAttribute('id', 'dao' + daocount + '|role' + nextfile);
   	role.setAttribute('value', 'reference');
   	doform.insertBefore(role, tbody.parentNode);				
		
}

function createDaoForm(){

	var container = document.getElementById('daocontainer');
	var create = document.getElementById('createnewdao');
	var type = document.getElementById('daoselect').value;

	if (type != 'null'){
		var doform = document.createElement('div');
		daocount++;
		doform.setAttribute('id', 'daoform' + daocount);
		doform.className = type; 
		
		if (type == 'new' || type == 'embed') {
		
			var span = document.createElement('b');
			if (type == 'new'){
				var text = document.createTextNode('Link to file');
			}
			if (type == 'embed'){
				var text = document.createTextNode('Display image');
			}
			span.appendChild(text);
		
			var table = document.createElement('table');
			table.className = 'daotable';
   			var tbody = document.createElement('tbody');
   			
   			
   		//file location   			
   			var tr = document.createElement('tr');
   			var td = document.createElement('td');
   			td.appendChild(document.createTextNode('File URI: '));
   			td.className = 'label';
   			tr.appendChild(td);
   			
   			var href = document.createElement('input');
   			href.setAttribute('type', 'text');
   			href.onclick = function () {setCurrent(this); },
   			href.setAttribute('name', 'dao' + daocount + '|href' );
   			href.setAttribute('id', 'dao' + daocount + '|href' );
   			href.setAttribute('size', '70');
   			td = document.createElement('td');		
   			td.appendChild(href);
   			
   			tr.appendChild(td);
   			
   			tbody.appendChild(tr);



	//DAO desciption
   			tr = document.createElement('tr');
   			td = document.createElement('td');
   			td.appendChild(document.createTextNode('Description: '));
   			td.className = 'label';
   			tr.appendChild(td);
   			
   			var desc = document.createElement('input');
   			desc.setAttribute('type', 'text');   			
			desc.onclick = function () {setCurrent(this); },
			desc.onkeypress = function () {validateFieldDelay(this, 'true'); },
			desc.onchange = function () {validateField(this, 'true') },
   			desc.setAttribute('name', 'dao' + daocount + '|desc' );
   			desc.setAttribute('id', 'dao' + daocount + '|desc' );
   			desc.setAttribute('size', '70');
   			desc.setAttribute('value', '<p></p>');
   			desc.className = 'menuField';
 			td = document.createElement('td');
   			td.appendChild(desc);
   			
   			tr.appendChild(td);
   			
   			tbody.appendChild(tr);  			

 	//show  			   			
   			var show = document.createElement('input');
   			show.setAttribute('type', 'hidden');
   			show.setAttribute('name', 'dao' + daocount + '|' + type );
   			show.setAttribute('value', type);

	//delete button
	
			var button = document.createElement('input');
			button.setAttribute('type', 'button');
			var string = 'daoform' + daocount;
			button.onclick = function () {deleteDao(string); },
			button.value = 'Delete';
			
			
			table.appendChild(tbody);
			doform.appendChild(span);
			doform.appendChild(table);
   			doform.appendChild(show);
   			doform.appendChild(button);
   			container.insertBefore(doform, create);   
   			   			
		} 
		else if (type=='thumb') {
		
			var span = document.createElement('b');
			var text = document.createTextNode('Thumbnail link to file');		
			span.appendChild(text);
				
			var table = document.createElement('table');
			table.className = 'daotable';
   			var tbody = document.createElement('tbody');

	//thumbnail location   			
  			var tr = document.createElement('tr');
   			var td = document.createElement('td');
   			td.appendChild(document.createTextNode('Thumbnail URI: '));
   			td.className = 'label';
   			tr.appendChild(td);
   			
   			var href = document.createElement('input');
   			href.setAttribute('type', 'text');
   			href.onclick = function () {setCurrent(this); },
   			href.setAttribute('name', 'dao' + daocount + '|href1' );
   			href.setAttribute('id', 'dao' + daocount + '|href1' );
   			href.setAttribute('size', '70');
   			td = document.createElement('td');		
   			td.appendChild(href);
   			
   			tr.appendChild(td);   			
   			tbody.appendChild(tr);  
   			
   	//role info
    		var role1 = document.createElement('input');
   			role1.setAttribute('type', 'hidden');
   			role1.setAttribute('name', 'dao' + daocount + '|thumb');
   			role1.setAttribute('id', 'dao' + daocount + '|thumb');
   			role1.setAttribute('value', 'thumb');
   			

	//file location
  			tr = document.createElement('tr');
   			td = document.createElement('td');
   			td.appendChild(document.createTextNode('File URI: '));
   			td.className = 'label';
   			tr.appendChild(td);
   			
   			href = document.createElement('input');
   			href.setAttribute('type', 'text');
   			href.onclick = function () {setCurrent(this); },
   			href.setAttribute('name', 'dao' + daocount + '|href2' );
   			href.setAttribute('id', 'dao' + daocount + '|href2' );
   			href.setAttribute('size', '70');
   			td = document.createElement('td');		
   			td.appendChild(href);
   			
   			tr.appendChild(td);   			
   			tbody.appendChild(tr);  


 	//role info
    		var role2 = document.createElement('input');
   			role2.setAttribute('type', 'hidden');
   			role2.setAttribute('name', 'dao' + daocount + '|reference');
   			role2.setAttribute('id', 'dao' + daocount + '|reference');
   			role2.setAttribute('value', 'reference');


	//DAO desciption
   			tr = document.createElement('tr');
   			td = document.createElement('td');
   			td.appendChild(document.createTextNode('Description: '));
   			td.className = 'label';
   			tr.appendChild(td);
   			
   			var desc = document.createElement('input');
   			desc.setAttribute('type', 'text');
   			desc.onclick = function () {setCurrent(this); },
			desc.onkeypress = function () {validateFieldDelay(this, 'true'); },
			desc.onchange = function () {validateField(this, 'true') },
   			desc.setAttribute('name', 'dao' + daocount + '|desc' );
   			desc.setAttribute('id', 'dao' + daocount + '|desc' );
   			desc.setAttribute('size', '70');
   			desc.setAttribute('value', '<p></p>');
   			desc.className = 'menuField';
 			td = document.createElement('td');
   			td.appendChild(desc);
   			
   			tr.appendChild(td);   			
   			tbody.appendChild(tr);  			

		
	//delete button
	
			var button = document.createElement('input');
			button.setAttribute('type', 'button');
			var string = 'daoform' + daocount;
			button.onclick = function () {deleteDao(string); },
			button.value = 'Delete';			
			
			
			table.appendChild(tbody);
			doform.appendChild(span);
			doform.appendChild(table);	
			doform.appendChild(role1);
			doform.appendChild(role2);
			doform.appendChild(button);
   			container.insertBefore(doform, create);   
		
		}
		else if (type=='multiple'){
		
			var span = document.createElement('b');
			var text = document.createTextNode('Link to multiple files');		
			span.appendChild(text);
		
   		   	var table = document.createElement('table');
   		   	table.className = 'daotable';
   			var tbody = document.createElement('tbody');
   			var start = 2;
   			for (var i=1; i<=start; i++){
   			
   				if (i%2 == 0){
   					var shading = 'odd';
   				}
   				else {
   					var shading = 'even';
   				}
   			//file uri
   				var tr = document.createElement('tr');
   				tr.className = shading;
   				var td = document.createElement('td');
   				td.appendChild(document.createTextNode('File ' + i + ' URI: '));
   				td.className = 'label';
   				tr.appendChild(td);
   				
	   			href = document.createElement('input');
	   			href.setAttribute('type', 'text');
	   			href.onclick = function () {setCurrent(this); },
	   			href.setAttribute('name', 'dao' + daocount + '|href' + i);
	   			href.setAttribute('id', 'dao' + daocount + '|href' + i);
	   			href.setAttribute('size', '70');
	   			td = document.createElement('td');		
	   			td.appendChild(href);
	   			
	   			tr.appendChild(td);
	   			
	   			tbody.appendChild(tr);     	
	   			
	   			
		//file title   			
	  			tr = document.createElement('tr');
	  			tr.className = shading;
	   			td = document.createElement('td');
	   			td.appendChild(document.createTextNode('File ' + i + ' title: '));
	   			td.className = 'label';
	   			tr.appendChild(td);
	   			
	   			href = document.createElement('input');
	   			href.setAttribute('type', 'text');
	   			href.onclick = function () {setCurrent(this); },
	   			href.setAttribute('name', 'dao' + daocount + '|title' + i);
	   			href.setAttribute('id', 'dao' + daocount + '|title' + i);
	   			href.setAttribute('size', '70');
	   			td = document.createElement('td');		
	   			td.appendChild(href);
	   			
	   			tr.appendChild(td);
	   			
	   			tbody.appendChild(tr);  
	   			 
	 	//role info
	    		role = document.createElement('input');
	   			role.setAttribute('type', 'hidden');
	   			role.setAttribute('name', 'dao' + daocount + '|role' + i);
	   			role.setAttribute('id', 'dao' + daocount + '|role' + i);
	   			role.setAttribute('value', 'reference');
	   			doform.appendChild(role);			
   			}
   			
   			tr = document.createElement('tr');
   			td = document.createElement('td');
   			td.className = 'label';
   			tr.appendChild(td);
   			
   			td = document.createElement('td');
   			var link = document.createElement('a');
  			link.appendChild(document.createTextNode('add another file'));
   			link.className = 'smalllink';
   			var string = 'daoform' + daocount;
  			link.onclick = function () {addFile(string); };
   			td.appendChild(link);
   			tr.appendChild(td);
   			
   			tbody.appendChild(tr); 
   			
   		//DAO desciption
   			tr = document.createElement('tr');
   			td = document.createElement('td');
   			td.appendChild(document.createTextNode('Description of group: '));
   			td.className = 'label';
   			tr.appendChild(td);
   			
   			var desc = document.createElement('input');
   			desc.setAttribute('type', 'text');
   			desc.onclick = function () {setCurrent(this); },
			desc.onkeypress = function () {validateFieldDelay(this, 'true'); },
			desc.onchange = function () {validateField(this, 'true') },
   			desc.setAttribute('name', 'dao' + daocount + '|desc');
   			desc.setAttribute('id', 'dao' + daocount + '|desc');
   			desc.setAttribute('size', '70');
   			desc.setAttribute('value', '<p></p>');
   			desc.className = 'menuField';
 			td = document.createElement('td');
   			td.appendChild(desc);
   			
   			tr.appendChild(td);
   			
   			tbody.appendChild(tr);  	
   			
   			
   		//delete button
	
			var button = document.createElement('input');
			button.setAttribute('type', 'button');
			var string = 'daoform' + daocount;
			button.onclick = function () {deleteDao(string); },
			button.value = 'Delete';	
   			
   			table.appendChild(tbody);
   			doform.appendChild(span);
			doform.appendChild(table);
			doform.appendChild(button);
   			container.insertBefore(doform, create);   			
   		}
		
	}
	document.getElementById('daoselect').value = 'null';
}


function deleteDao(id){

	var container = document.getElementById('daocontainer');
	var form = document.getElementById(id);	
	container.removeChild(form);
	
}



function checkButtons(){
	if (document.getElementById('pui').value.strip() == ''){
		document.getElementById('xml-button').setAttribute('disabled', 'true');
		document.getElementById('xml-button').setAttribute('title', 'File must be saved before this operation can be performed');
		document.getElementById('preview-button').setAttribute('disabled', 'true');
		document.getElementById('preview-button').setAttribute('title', 'File must be saved before this operation can be performed');
		document.getElementById('tofile-button').setAttribute('disabled', 'true');
		document.getElementById('tofile-button').setAttribute('title', 'File must be saved before this operation can be performed');
		document.getElementById('submit-button').setAttribute('disabled', 'true');
		document.getElementById('submit-button').setAttribute('title', 'File must be saved before this operation can be performed');		
		document.getElementById('addC').setAttribute('disabled', 'true');
		document.getElementById('addC').setAttribute('title', 'File must be saved before this operation can be performed');			
	}
}

function enableMenuButtons(){
	var inputs = document.getElementsByTagName('input');
	for (var i=0; i< inputs.length; i++){
		if (inputs[i].getAttribute('type') == 'button' || inputs[i].getAttribute('type') == 'submit'){
			inputs[i].removeAttribute('disabled');
		}
	}
	var select = document.getElementById('userSelect');
	if (select) {
	    select.removeAttribute('disabled');
	}
}


