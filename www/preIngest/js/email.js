/*
// Script:   	email.js
// Version:   0.01
// Description:
//            JavaScript functions used in the Cheshire3 EAD search/retrieve and display interface 
//            - part of Cheshire for Archives v3.x
//
// Language:  JavaScript
// Author:    John Harrison <john.harrison@liv.ac.uk>
// Date:      03 August 2006
//
// Copyright: &copy; University of Liverpool 2005, 2006
//
// Version History:
// 0.01 - 03/08/2006 - JH - Email address verification function(s) pasted in from previous script
//
*/

function checkEmailAddy(){
	var addy = document.email.address.value;
	var emailRe  = /^[a-zA-Z][^@ .]*(\.[^@ .]+)*@[^@ .]+\.[^@ .]+(\.[^@ .]+)*$/;
	if(emailRe.test(addy)) {
		return true;
	}
	else {
		alert('Your address did not match the expected form: name@company.domain\n\nPlease re-enter your address.');
		return false;
	}
}

function addFormValidation(){
	if( !document.getElementsByTagName) {
  		return;
  	}	
  	var forms = document.getElementsByTagName("form");
  	for (var i = 0; i < forms.length; i++) {
		if (forms[i].className.match('email')){
			forms[i].onsubmit = function() { return checkEmailAddy(); }
		}
	}
}

if (addLoadEvent) {
	addLoadEvent(addFormValidation);
} else {
	window.onload = addFormValidation;
}
