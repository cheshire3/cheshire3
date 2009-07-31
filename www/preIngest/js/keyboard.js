/*
// Program:		keyboard.js
// Version:   	0.02
// Description:
//            	JavaScript functions for input of special characters into the ead template.  
//            	- produced for the Archives Hub v3.x. 
// Language:  	JavaScript
// Author(s):   John Harrison <john.harrison@liv.ac.uk>
//				Catherine Smith <catherine.smith@liv.ac.uk>
// Date:      	09/01/2009
// Copyright: 	&copy; University of Liverpool 2005-2009
//
// Version History:
// 0.01 - 08/08/2006 - JH - basic functions completed for original ead2002 template
// 0.02 - 09/01/2009 - CS - Addition of code to maintain current scroll position in text area after adding character
//							field codes changes to represent new ead editing interface
*/



var	currentEntryField = null;
var	theFieldName = "Error. You have not yet selected a field to enter text into.";

var fieldMap = new Array();

	fieldMap['countrycode'] = 'Country Code';
	fieldMap['archoncode'] = 'Archon Code';
	fieldMap['unitid'] = 'Unit ID';
	fieldMap['did/unittitle'] = 'Title';
	fieldMap['did/unitdate'] = 'Dates of Creation';
	fieldMap['did/unitdate/@normal'] = 'Normalised Date - This should NOT contain character entities';
	fieldMap['did/physdesc/extent'] = 'Extent of Unit Description';
	fieldMap['did/repository'] = 'Repository';
	fieldMap['filedesc/titlestmt/sponsor'] = 'Sponsor';
	fieldMap['did/origination'] = 'Name of Creator';
	fieldMap['bioghist'] = 'Administrative/Biographical History';
	fieldMap['custodhist'] = 'Archival History';
	fieldMap['acqinfo'] = 'Immediate Source of Acquisition';
	fieldMap['scopecontent'] = 'Scope and Content';
	fieldMap['appraisal'] = 'Appraisal';
	fieldMap['accruals'] = 'Accruals';
	fieldMap['arrangement'] = 'System of Arrangement';
	fieldMap['accessrestrict'] = 'Conditions Governing Access';
	fieldMap['userestrict'] = 'Conditions Governing Reproduction';
	fieldMap['lang_name'] = 'Language of Material - Language Name';
	fieldMap['lang_code'] = 'Language of Material - Language Code - This should NOT contain character entities';
	fieldMap['phystech'] = 'Physical Characteristics';
	fieldMap['otherfindaid'] = 'Finding Aids';
	fieldMap['originalsloc'] = 'Existence/Location of Orginals';
	fieldMap['altformavail'] = 'Existence/Location of Copies';
	fieldMap['relatedmaterial'] = 'Related Units of Description';
	fieldMap['bibliography'] = 'Publication Note';
	fieldMap['note'] = 'Note';
	fieldMap['processinfo'] = 'Archivist\'s Note';
	fieldMap['dao/@href'] = 'Digital Object - URI';
	fieldMap['did/dao/@href'] = 'Digital Object - URI';
	fieldMap['dao/@title'] = 'Digital Object - Title';
	fieldMap['did/dao/@title'] = 'Digital Object - Title';
	fieldMap['dao/daodesc'] = 'Digital Object - Description';
	fieldMap['did/dao/daodesc'] = 'Digital Object - Description';
	fieldMap['daogrp/daoloc/@href'] = 'Digital Object - URI';
	fieldMap['did/daogrp/daoloc/@href'] = 'Digital Object - URI';
	fieldMap['daogrp/daoloc/@title'] = 'Digital Object - Title';
	fieldMap['did/daogrp/daoloc/@title'] = 'Digital Object - Title';
	fieldMap['daogrp/daodesc'] = 'Digital Object - Description';
	fieldMap['did/daogrp/daodesc'] = 'Digital Object - Description';
	fieldMap['persname_surname'] = 'Personal Name - Surname';
	fieldMap['persname_forename'] = 'Personal Name - Forename';
	fieldMap['persname_dates'] = 'Personal Name - Dates';
	fieldMap['persname_title'] = 'Personal Name - Title';
	fieldMap['persname_epithet'] = 'Personal Name - Epithet';
	fieldMap['persname_other'] = 'Personal Name - Other';
	fieldMap['persname_source'] = 'Personal Name - Source';
	fieldMap['famname_surname'] = 'Family Name - Surname';
	fieldMap['famname_other'] = 'Family Name - Other';
	fieldMap['famname_dates'] = 'Family Name - Dates';
	fieldMap['famname_title'] = 'Family Name - Title';
	fieldMap['famname_epithet'] = 'Family Name - Epithet';
	fieldMap['famname_loc'] = 'Family Name - Location';
	fieldMap['famname_source'] = 'Family Name - Source';
	fieldMap['corpname_organisation'] = 'Corporate Name - Organisation';
	fieldMap['corpname_dates'] = 'Corporate Name -_Dates';
	fieldMap['corpname_loc'] = 'Corporate Name - Location';
	fieldMap['corpname_other'] = 'Corporate Name - Other';
	fieldMap['corpname_source'] = 'Corporate Name - Source';
	fieldMap['subject_subject'] = 'Subject';
	fieldMap['subject_dates'] = 'Subject - Dates';
	fieldMap['subject_loc'] = 'Subject - Location';
	fieldMap['subject_other'] = 'Subject - Other';	
	fieldMap['subject_source'] = 'Subject - Thesaurus';
	fieldMap['geogname_location'] = 'Place Name - Location';
	fieldMap['geogname_other'] = 'Place Name - Other';
	fieldMap['geogname_source'] = 'Place Name - Source';
	fieldMap['title_title'] = 'Book Title';
	fieldMap['title_dates'] = 'Book Title - Dates';
	fieldMap['title_source'] = 'Book Title - Source';
	fieldMap['genreform_genre'] = 'Genre Form';	
	fieldMap['genreform_source'] = 'Genre Form - Source';	
	fieldMap['function_function'] = 'Function';
	fieldMap['function_source'] = 'Function - Source';
			
	
	function getFieldName(code){
		if (code.indexOf('[') != -1){
			var lookup = code.replace(/\[[0-9]+\]/g, '');
		}
		else {
			var lookup = code;
		}
		return fieldMap[lookup];
	}
	
	function setCurrent(which) {
	  // onChange fires only when focus leaves, so use onFocus
	  if (which == 'none'){
	  	currentEntryField = null;
	  	theFieldName = "Error. You have not yet selected a field to enter text into.";
	  }
	  else {
	  	currentEntryField = which;
	  	theFieldName = getFieldName(which.id);
	  }
	}



function cursorInsert(field, insert) {
	/*
	// Description: a function to insert text at the cursor position in a specified field (textarea, text)
	*/
	if (insert == 'quot'){
		insert = '"';
	}
	if (field){
		//get scroll position
		var scrollPos = field.scrollTop;
		if (field.selectionStart || field.selectionStart == '0') {
			// Firefox 1.0.7, 1.5.0.6 - tested
			var startPos = field.selectionStart;
			var endPos = field.selectionEnd;
			if (endPos < startPos)	{
	          var temp = end_selection;
	          end_selection = start_selection;
	          start_selection = temp;
			}
			var selected = field.value.substring(startPos, endPos);
			field.value = field.value.substring(0, startPos) + insert + field.value.substring(endPos, field.value.length);
			//for FF at least we can get the curser to stay after the entered letter instead of at end of field
			//see http://www.scottklarr.com/topic/425/how-to-insert-text-into-a-textarea-where-the-cursor-is/ for possible improvements to IE version
			field.focus(); 
			field.selectionEnd = endPos + 1;
			field.selectionStart = endPos + 1;
		}
		else {
			 if (document.selection) {
				//Windows IE 5+ - tested
				field.focus();
				selection = document.selection.createRange();
				selection.text = insert;
			}
			else if (window.getSelection) {
				// Mozilla 1.7, Safari 1.3 - untested
				selection = window.getSelection();
				selection.text = insert;
			}
			else if (document.getSelection) {
				// Mac IE 5.2, Opera 8, Netscape 4, iCab 2.9.8 - untested
				selection = document.getSelection();
				selection.text = insert;
			} 
			else {
				field.value += insert;
			}
			field.focus(); //this puts cursor at end
		}
		//reset scroll to right place in text box
		if (scrollPos){
			field.scrollTop = scrollPos;
		}
	}
}
		
