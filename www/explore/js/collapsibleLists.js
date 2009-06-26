/*
// Script:   	collapsibleLists.js
// Version:   	0.02
// Description:
//            JavaScript functions used in the Cheshire3 EAD search/retrieve and display interface 
//            - part of Cheshire for Archives v3.x
//
// Language:  	JavaScript
// Authors:     John Harrison <john.harrison@liv.ac.uk>
//				Catherine Smith <catherine.smith@liv.ac.uk>
// Date:      	11 January 2008
//
// Copyright: &copy; University of Liverpool 2005-2008
//
// Version History:
// 0.01 - 03/08/2006 - JH - Nested list manipulation functions pasted in from previous script for easier error tracking etc.
// 0.02 - 11/01/2008 - CS - Code adapted to allow list to begin collapsed or uncollapsed (collapseList boolean) and to allow
//							for either each level to be controlled to that only one folder from it can be open at a time or not
//							(controlLevels boolean)
						  - Function names changed to be more generic (necessary changes made in eadAdminHandler.py, htmlFragments.py and eadEditingHandler
*/

/* Note: list must be well formed, all tags closed, 
// all sublists must be contained within a list item,
// NOT a direct descendent of parent list.
*/

var expandedLists = [];
var listCount = 0;

/* customisable display of icons in collapsible lists */
/* file explorer style */
var collapsedUrl = '/ead/img/folderClosed.gif';
var expandedUrl = '/ead/img/folderOpen.gif';
var itemUrl = '/ead/img/folderItem.jpg';
var lastItemUrl = '/ead/img/folderItem.jpg';
/* skeletal style - uncomment/comment to replace the above defaults */
//var collapsedUrl = '/ead/img/barPlus.gif';
//var expandedUrl = '/ead/img/barMinus.gif';
var itemUrl = '/ead/img/barT.gif'
var lastItemUrl = '/ead/img/barLast.gif'


function createTreeFromList(listId, treeState, collapseList, controlLevels) {

  	/* args: 
     	listId -> str - id attr of list to collapse
     	treeState -> str - string representation of state of list
     	collapseChildren -> bool - collapse the tree? if this is false controlLevels must also be false (is reset here just in case)
     	controlLevels -> bool - control Levels so that only one folder at each level can be open at any time
  	*/
  	if( !document.getElementsByTagName || !document.childNodes || !document.createElement ) {
  		return;
  	}	
 	var rootListObj = document.getElementById( listId ); 
  	if( !rootListObj ) { 
    	return; 
  	}
  	if (!collapseList){
  		controlLevels = false;
  	}
  	createSubLists(rootListObj, 0, listId, treeState, collapseList, controlLevels, rootListObj.tagName.toLowerCase());
}


function createSubLists(listObj, level, rootListId, treeState, collapseList, controlLevels, listTag) {
  	/* args: 
     	listObj -> obj - root node of tree to collapse
     	level -> int - level of the sub-list we're collapsing
     	rootListId -> str - id attr of root list
     	treeState -> str - string representation of state of list
     	collapseChildren -> bool - collapse the tree?
     	controlLevels -> bool - control Levels so that only one folder at each level can be open at any time
     	listTag - str - tag used for root list 'ul' or 'ol' 
  	*/
 
 	var temp = listObj.childNodes;
 	var listItems = []
 	var j = 0;
 	for (var i=0; i<temp.length; i++){
 		if (temp[i].tagName == 'LI'){
 			listItems[j] = temp[i];
 			j++;
 		}	
 	}
  	tocLevels = treeState.split(':');
  	if( !level ) { 
		rootListId = escape(rootListId); 
  		if( collapseList ) { 
      		expandedLists[rootListId] = []; 
    	}
    	else {
    		expandedLists[rootListId] = []; 
    	}
  	}
  	for( var i = 0 ; i < listItems.length; i++ ) { 
	    // for each <li>
	    if( listItems[i].tagName) {
	      	var nextSubList = listItems[i].getElementsByTagName( listTag )[0];
	      	if( nextSubList ) {    	
	      		if (collapseList){
					//collapse 1st sub-list
					nextSubList.style.display = 'none';
				}
				//create a link for expanding/collapsing
				var newLink = document.createElement('a');
				newLink.setAttribute( 'href', '#' );
				newLink.onclick = new Function( 'switchState(this,' + level + ',\'' + rootListId + '\',' + controlLevels + ',\'' + escape(listTag) + '\');return false;' );
				// wrap everything upto child list in the link
				var imgElem = document.createElement('img');
				var countElem = document.createElement('span');
				countElem.setAttribute( 'class', 'subcount');
				var countTxt = document.createTextNode(' {' + nextSubList.getElementsByTagName('li').length + ' entries}');
				countElem.appendChild(countTxt);

				if (tocLevels[level] && listCount == tocLevels[level] || !collapseList) {
					//re-inflate 1st sub-list
					nextSubList.style.display = 'block';
				  	imgElem.setAttribute( 'src', expandedUrl );
				  	imgElem.setAttribute( 'alt', '[-]');
				  	expandedLists[rootListId][level] = nextSubList;
				}
				else {
				  	imgElem.setAttribute( 'src', collapsedUrl );
				  	imgElem.setAttribute( 'alt', '[+]');
				}

				newLink.appendChild(imgElem);
				
				listItems[i].insertBefore(newLink, listItems[i].childNodes[0]);
				for (var j =0; j< listItems[i].childNodes.length; j++){
					if (listItems[i].childNodes[j].tagName == 'UL'){
						listItems[i].insertBefore(countElem, listItems[i].childNodes[j]);
					}
				}			
				nextSubList.colListId = listCount++;
				createSubLists( nextSubList, level + 1, rootListId, treeState, collapseList, controlLevels, listTag);
	      	}       
		    else {

				var imgElem = document.createElement('img');
				if (i < listItems.length-1){
					imgElem.setAttribute( 'src', itemUrl );
				} else {
					imgElem.setAttribute( 'src', lastItemUrl );
				}
				imgElem.setAttribute( 'alt', '-');
				listItems[i].insertBefore(imgElem, listItems[i].childNodes[0]);
		   	}
    	} 
  	} 
}


function switchState( thisObj, level, rootListId, controlLevels, listTag ) {
  	/* args:
     	thisObj = obj - node of tree to switch state expanded/collapsed
     	level = int - level of element being switched
     	rootListId -> str - id attr of root list
     	collapseChildren -> bool - keep sub-lists collapsed?
     	listTag - str - tag used for root list 'ul' or 'ol' 
   	*/
   	
   	if( thisObj.blur ) { 
    	thisObj.blur(); 
  	}
  	var linkElem = thisObj.parentNode.getElementsByTagName( 'a' )[0];
  	thisObj = thisObj.parentNode.getElementsByTagName( unescape(listTag) )[0];
  	if (!controlLevels){
  		if (linkElem) {
    		var imgElem = linkElem.getElementsByTagName( 'img' )[0];
    		if (imgElem) {
      			if (thisObj.style.display == 'block') {
      				imgElem.setAttribute( 'src', collapsedUrl);
					thisObj.style.display = 'none';
      			} else {
      				imgElem.setAttribute( 'src', expandedUrl);
					thisObj.style.display = 'block';
      			}
    		}
  		} 	
  	}
  	else {
  		var imgElem = linkElem.getElementsByTagName( 'img' )[0];
  		if (imgElem) {
      		if (imgElem.getAttribute('src') == expandedUrl) {
				imgElem.setAttribute( 'src', collapsedUrl);
				
      		} 
      		else {
				imgElem.setAttribute( 'src', expandedUrl);
				 
      		}
    	}
  		for( var x = expandedLists[rootListId].length - 1; x >= level; x-=1 ) { 
      		if( expandedLists[rootListId][x] ) {
				expandedLists[rootListId][x].style.display = 'none';
				var linkElem = expandedLists[rootListId][x].parentNode.getElementsByTagName('a')[0];
				if (linkElem) {
				 	var imgElem = linkElem.getElementsByTagName( 'img' )[0];
				  	if (imgElem) {
				    	imgElem.setAttribute( 'src', collapsedUrl);
				    	thisObj.style.display = 'none';
				  	}
				}
				if( level != x ) { 
				  	expandedLists[rootListId][x] = null; 
				}
      		} 
    	}
    	if( thisObj == expandedLists[rootListId][level] ) {
      		expandedLists[rootListId][level] = null; 
    	} 
    	else { 
      		thisObj.style.display = 'block'; 
      		expandedLists[rootListId][level] = thisObj; 
    	}
  	}
}


function refreshTree(listId){
	if( !document.getElementsByTagName || !document.childNodes || !document.createElement ) {
  		return;
  	}	
 	var rootListObj = document.getElementById( listId );

  	if( !rootListObj ) { 
    	return; 
  	}
  	refreshSubTrees(rootListObj, 0, listId, rootListObj.tagName.toLowerCase());
}


function refreshSubTrees(listObj, level, rootListId, listTag){
	
	var temp = listObj.childNodes;
 	var listItems = [];
 	var j = 0;
 	for (var i=0; i<temp.length; i++){
 		if (temp[i].tagName == 'LI'){
 			listItems[j] = temp[i];
 			j++;
 		}	
 	}
 	expandedLists[rootListId] = [];
 	for( var i = 0 ; i < listItems.length; i++ ) { 
	    // for each <li>
	    if( listItems[i].tagName) {
	      	var nextSubList = listItems[i].getElementsByTagName( listTag )[0];
	      	if( nextSubList ) {    	      			
	      		var image = listItems[i].getElementsByTagName('IMG')[0];
	      		source = image.getAttribute('src');
				if (source.substring(source.lastIndexOf('/')) == '/folderOpen.gif' || source.substring(source.lastIndexOf('/')) == '/folderClosed.gif'){
					var span = listItems[i].getElementsByTagName('SPAN')[0];
					span.firstChild.nodeValue = ' {' + nextSubList.getElementsByTagName('li').length + ' entries}';			
				}
				else {
					image = listItems[i].getElementsByTagName('IMG')[0];
					try{
						listItems[i].removeChild(image);
					}
					catch (e){
						image.parentNode.removeChild(image);
					}
					//create a link for expanding/collapsing
					var newLink = document.createElement('a');
					newLink.setAttribute( 'href', '#' );
					newLink.onclick = new Function( 'switchState(this,' + level + ',\'' + rootListId + '\',' + false + ',\'' + escape(listTag) + '\');return false;' );
					// wrap everything upto child list in the link
					var imgElem = document.createElement('img');
					var countElem = document.createElement('span');
					countElem.className = 'subcount';
					var countTxt = document.createTextNode(' {' + nextSubList.getElementsByTagName('li').length + ' entries}');
					countElem.appendChild(countTxt);

					imgElem.setAttribute( 'src', expandedUrl );
					imgElem.setAttribute( 'alt', '[-]');
	
					newLink.appendChild(imgElem);
					
					listItems[i].insertBefore(newLink, listItems[i].childNodes[0]);
					for (var j =0; j< listItems[i].childNodes.length; j++){
						if (listItems[i].childNodes[j].tagName == 'UL'){
							listItems[i].insertBefore(countElem, listItems[i].childNodes[j]);
						}
					}								
				}
				nextSubList.colListId = listCount++;
				refreshSubTrees(nextSubList, level+1, rootListId, listObj.tagName.toLowerCase())
	      	}       
		    else {
		    	//remove the straight images
				if (listItems[i].childNodes[0].tagName == 'IMG'){
					listItems[i].removeChild(listItems[i].childNodes[0]);
				}
				//remove folder images (wrapped in links)
				else if (listItems[i].childNodes[0].childNodes[0].tagName == 'IMG'){	
					listItems[i].removeChild(listItems[i].childNodes[0]);				
					//these will also have span class=subcount which needs deleting first
					var children = listItems[i].childNodes;
					for (var j=0; j< children.length; j++){
						if (children[j].tagName == 'SPAN'){
							var span = children[j];
							if (span.className == 'subcount'){
								listItems[i].removeChild(span);
							}
						}
					} 					
				}
				var imgElem = document.createElement('img');
				if (i < listItems.length-1){
					imgElem.setAttribute( 'src', itemUrl );
				} else {
					imgElem.setAttribute( 'src', lastItemUrl );
				}
				imgElem.setAttribute( 'alt', '-');
				listItems[i].insertBefore(imgElem, listItems[i].childNodes[0]);
		   	}
    	} 
  	} 
}


function stateToString(listId) {
  	/* args:
     listId = str - id attr of list to create string representation of state for
  	*/
  	if( !document.getElementsByTagName || !document.childNodes || !document.createElement ) { 
    	return ''; 
  	}
  	var rootListObj = document.getElementById(listId);
  	if (!rootListObj) {
    	return '';
  	}

  	var stateStr = ''
  	for (var level = 0; level < expandedLists[listId].length; level++) {
    	var listObj = expandedLists[listId][level]
    	if (listObj) {
      		stateStr += listObj.colListId + ':';
    	}
  	}
  	return stateStr;
}


function isInArray(obj, array) {
  	/* args:
     obj = obj - the object to look for existence of
     array = obj - array object to search in
  	*/
  	for(var i = 0; i < array.length; i++) { 
    	if(obj == array[i]) { 
      		return true;
    	}
  	} 
  	return false;
}
