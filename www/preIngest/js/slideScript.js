//////////////////////////////////////////////////////////////////////////////
//                      Show/Hide With a Slide Script                       //
//////////////////////////////////////////////////////////////////////////////
// 
// This little script allows you to create a section of content and hide it at
// the top of your screen for users to open and close as they wish.  This is
// particularly handy for things like login boxes, supplementary navigation
// and content enhancements like tips, tricks and interesting tidbits of
// information you don't need showcased within your regular content.
//
// If a visitor has JavaScript disabled or unavailable, the hidden content box
// will simply display itself as if it was always a visible component.
//
// CONTRIBUTORS:
//
// Original Creator:
//     Paul Hirsch
//     www.paulhirsch.com
//
// Tested by:
//     International Web Developers Network (IWDN)
//     www.iwdn.net - home page
//     www.iwdn.net/index.php - forums/community where testing took place
//
// Other Contributors:
//     Michaeljohn Clement - clued me in on offsetHeight - very handy!
//     [INSERT YOUR NAME AND BRIEF DESCRIPTION OF YOUR CONTRIBUTION HERE]
//
// INSTRUCTIONS:
//
// 1.  Place this markup in an external .js page and link to it within the
//     <head> section of your page.
//
// 2.  Create a div within your page, making it the VERY FIRST ELEMENT in
//     your markup.  You'll place your hidden content in here. The div MUST
//     be in the following format: <div id="foo-#">, where:
//
//     a. "foo" is any word of your choice.
//     b. "-#" is any number between "-1" and "-9".
//
//     The "-#" sets the speed at which the box shows/hides itself, with 1
//     being slowest and 9 fastest.  If you forget to add your speed number
//     or add it incorrectly, the script will default to 5.
//     
//     Here's a proper example:
//     <div id="login-7">
//        [The stuff you want to show/hide]
//     </div>
//
// 3.  Add onclick="toggle();" and id="toggle" to whatever element you'd like
//     to use to toggle the hidden content box.  MAKE THE TOGGLED
//     OBJECT/TEXT/BUTTON display:none WITHIN YOUR STYLESHEET!  The script will
//     unhide it.  This is so it will not show up when someone has JavaScript
//     disabled.
//
//     Here's a proper example:
//     <input type="button" id="toggle" onclick="toggle();" value="ON/OFF" />
//
// 4.  Add onload="setup();" to your <body> tag.
//
// LICENSE:
//
// This script is protected under General Public License (GPL).  Feel free to
// redistribute this script, so long as you do not alter any of the contents
// specifying authorship.  If you add to or modify this script, you may add
// your name to the "Other Contributors" list at the top of this script.  As
// a courtesy, please email me and let me know how you've improved my script!
// You may not profit from the direct sale of this script.  You may use this
// script in commercial endeavors however (i.e. as part of a commercial site).
//
// Email me here: http://www.paulhirsch.com/contact_me.php
//
// Copyright 2006, Paul Hirsch. All rights specified herein and within GPL
// documentation: http://www.gnu.org/licenses/gpl.txt
//
//////////////////////////////////////////////////////////////////////////////
// DO NOT TOUCH ANYTHING BELOW THIS LINE                                    //
// unless you know what the heck you're doing!                              //
//////////////////////////////////////////////////////////////////////////////

var Hide = "";
var varHt = "";
var Ht = "";
var x = 0;
var y = 10;
var z = 1;
var foo = new Array();
var Speed = "";

function setup() {
	//foo = document.getElementsByTagName("div");
	//Hide = foo[0].id;
	Hide = 'chartablelower';
	Ht = document.getElementById(Hide).offsetHeight;
	varHt = Ht;
	//Speed = Hide.substring(Hide.lastIndexOf('-')+1);
	Speed = 5
	document.getElementById(Hide).style.marginTop = '-'+document.getElementById(Hide).offsetHeight+'px';
	document.getElementById(Hide).style.height = document.getElementById(Hide).offsetHeight+'px';
	document.getElementById('toggle').style.display = "inline";
	
	if (Speed == 1) { y = 100; z = 1; }
	if (Speed == 2) { y = 70; z = 1; }
	if (Speed == 3) { y = 40; z = 1; }
	if (Speed == 4) { y = 20; z = 1; }
	if (Speed == 5) { y = 10; z = 1; }
	if (Speed == 6) { y = 10; z = 2; }
	if (Speed == 7) { y = 10; z = 4; }
	if (Speed == 8) { y = 10; z = 7; }
	if (Speed == 9) { y = 10; z = 10; }
}

function slideToggle() {
	if (x === 0) {
		document.getElementById(Hide).style.marginTop = "-"+varHt+"px";
		if ((varHt < z) && (varHt !== 0)) {
			varHt = 0;
		} else {
			varHt = varHt-z;
		}
		if (varHt >= 0) {
			setTimeout('toggle()',y);
		}
		if (varHt < 0) {
			varHt = 0;
			x = 1;
		}
	} else {
		document.getElementById(Hide).style.marginTop = "-"+varHt+"px";
		varHt = varHt+z;
		if (varHt <= Ht) {
			setTimeout('slideToggle()',y);
		}
		if (varHt > Ht) {
			varHt = Ht;
			document.getElementById(Hide).style.marginTop = "-"+varHt+"px";
			x = 0;
		}
	}
}




