

current = 0;
dateRe = new RegExp('[0-2][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]( [0-2][0-9]:[0-5][0-9]:[0-5][0-9])?');

typeHash = {};
rangeHash = {};


function createXMLHttpRequest() {
  var xmlHttp=null;
  try {
    // Firefox, Opera 8.0+, Safari
    xmlHttp=new XMLHttpRequest();
  }
  catch (e) {
    // Internet Explorer
    try {
      xmlHttp=new ActiveXObject("Msxml2.XMLHTTP");
    }
    catch (e) {
      try {
	xmlHttp=new ActiveXObject("Microsoft.XMLHTTP");
      }
      catch (e) {
	alert("Your browser does not support AJAX! Some functionality will  be unavailable.");
	return false;
      }
    }
  }
  return xmlHttp;
}


function sendQuery(url, func) {
  req = createXMLHttpRequest();
  req.onreadystatechange=func;
  req.open("GET",url,true);
  req.send(null);
  return false;
}

function queryObject(what, selElem) {
  url = "http://localhost/preIngest/sparql/" + what;


  nf = function() {
    if (req.readyState==4 && req.status==200) {
      if (selElem.childNodes.length > 0) {
    	  return;
      }
      typeHash[selElem.id] = {};
      rangeHash[selElem.id] = {};
      info = eval('(' + req.responseText + ')');            
      var opnElem = document.createElement('option');
      opnElem.value = ''
      opnElem.innerHTML = 'Select a Property...'
      selElem.appendChild(opnElem);	
      for (var i=0; i <info.length; i++) {
    	  var opnElem = document.createElement('option');
    	  opnElem.value = info[i]['rel'];
    	  //opnElem.innerHTML = info[i]['label'];
	  opnElem.innerHTML = info[i]['rel'];
    	  typeHash[selElem.id][info[i]['rel']] = info[i]['propType']
    	  rangeHash[selElem.id][info[i]['rel']] = info[i]['range']
    	  selElem.appendChild(opnElem);	
      }	
    }
  }
  sendQuery(url, nf);
}

function createOptions(typ) {
  var selectElem = document.createElement('select');
  selectElem.id = "sel_" + typ;  
  queryObject(typ, selectElem);
  //selectElem.onchange = updateSelect;
  return selectElem;
}

function createNewItemOptions(nodeType, table) {
	var tab = document.getElementById(table);
	var tr = document.createElement('tr');
	var td = document.createElement('td');

  
	// NOTE:  This doesn't work in firefox 2.x, rows not updated dynamically	

	if (nodeType) {
	    td.appendChild(createOptions(nodeType));
	} else {
	    td.appendChild(createOptions('ore:Aggregation'));
	}
	tr.appendChild(td);
	tab.appendChild(tr);
}

function loadRicoTree(xmlFileName){
	Rico.loadModule('Tree');
	var curTreeView;
	
	Rico.onLoad( function() {
  	// initialize tree
  	var options={
    	  showCheckBox : true,
    	  showLines    : false,
    	  showPlusMinus: false,
    	  showFolders  : true,
  	}
	tree1=new Rico.TreeControl("tree1", null, options);

	tree1.setTreeDiv('tree1');

	// add RootNode
	//addRootNode();
	tree1.addNode(0,'root','ResourceMap',1, 1);
	// open tree
  	tree1.open();
	});

}

function addRootNode(){
   // Add root node to the Resource Map DOM
   curResourceMapDOM = newDOMDocument("ResourceMap");  

   // TO-DO: save to server side using a call to Python
   // ...

   // Make the treeView a copy of the Resource Map DOM 
   //curTreeView.loadXML(curResourceMapDOM);

   //curTreeView.addNode(0,'root','ResourceMap',1, 1);
  
}


function createDataRow(table, pred, value) {
  current++;
  var tab = document.getElementById(table);
  var tr = document.createElement('tr');
  // NOTE:  This doesn't work in firefox 2.x, rows not updated dynamically
  if (tab.rows.length % 2) {
    tr.className = 'odd';
  } else {
    tr.className = 'even';
  }
  tr.id = "row_" + current;
  tab.appendChild(tr);
  var td = document.createElement('td');
  var rem = document.createElement('img');
  rem.src="http://www.openannotation.org/adore-djatoka/images/close.png";
  rem.onclick = new Function('removeRow(' + current + ')');
  td.appendChild(rem);
  tr.appendChild(td);
  var td = document.createElement('td');  
  td.appendChild(document.createTextNode(pred))
  tr.appendChild(td);
  var td = document.createElement('td');
  td.id = "val_cell_" + current;
  td.appendChild(document.createTextNode(value));
  tr.appendChild(td);
  var td = document.createElement('td');
  td.appendChild(document.createTextNode(' '));
  tr.appendChild(td);
}


function removeRow(x) {
  var tr = document.getElementById('row_' + x);
  par = tr.parentNode;
  par.removeChild(tr);
  pl = 0;
  for (e in par.childNodes) {
    if (par.childNodes[e].tagName == 'TR') {
      pl += 1;
    }
  }
  // others go in to tbody (apparently)
  if (pl < 1) {
    createRow(par.id);
  }
}
  

function updateSelect(event) {
  var opt = this.options[this.selectedIndex];
  val = opt.value;
  par = this.parentNode;
  par.removeChild(this);
  par.appendChild(document.createTextNode(val));  

  id = this.id
  row = id.substring(4, id.length);
  row = parseInt(row);
  dt = typeHash[id][val];
  rng = rangeHash[id][val];
  if (dt == 'ObjectProperty') {
    var val = document.createElement('input');
    val.type = "text";
    img = document.createElement('img');
    img.src= 'http://www.openannotation.org/adore-djatoka/images/forward.png';
    img.value = val.value;
    img.id = 'img_' + row;
    img.onclick = createNewTab;
    tr = document.getElementById('row_' + row);
    td = tr.childNodes[tr.childNodes.length -1];
    td.appendChild(img);    
    img.type = rng;
  } else {
    var val = document.createElement('input');
    val.type = "text";
  }
  val.id = "input_" + row;
  val.valType = dt;
  val.valRange = rng;
  val.onchange = finalizeRow;
  td = document.getElementById('val_cell_' + row);
  td.removeChild(td.childNodes[0]);
  td.appendChild(val);    
}


swapToTab = function() {
  tb = this.tabIdx;
  tabs = document.getElementById('myTabber');
  tabObj = tabs.tabber;
  tabObj.tabShow(tb);
}

createNewTab = function() {
  value = this.value;
  type = this.type;
  if (!value) {
    alert("You must enter a URI to describe");
  } else {
    tabs = document.getElementById('myTabber');
    tabObj = tabs.tabber;
    idx = value.lastIndexOf('/');
    if (idx > -1) {
      title = value.substring(idx+1, value.length);
    } else {
      title = value;
    }
    t = tabObj.newTab(title);
    newTable = document.createElement('table');
    newTable.className = 'padded-table';
    newTable.id = "dtable" + t.idx;
    newTable.type = type;
    newTable.cellspacing = 0;
    this.tabIdx = t.idx;
    this.onclick = swapToTab;
    tr = document.createElement('tr');
    th = document.createElement('th');
    th.appendChild(document.createTextNode('Subject'));
    tr.appendChild(th);
    th = document.createElement('th');
    th.appendChild(document.createTextNode('Predicate'));
    tr.appendChild(th);
    th = document.createElement('th');
    th.appendChild(document.createTextNode('Value'));
    tr.appendChild(th);
    th = document.createElement('th');
    tr.appendChild(th);
    newTable.appendChild(tr);
    tr = document.createElement('tr');
    td = document.createElement('td');
    td.setAttribute('colspan', '4');
    b = document.createElement('b');
    b.appendChild(document.createTextNode(value));
    td.appendChild(b);
    tr.appendChild(td);
    newTable.appendChild(tr);
    t.div.appendChild(newTable);

    // Put in autodiscovered info
    if (this.addInfo) {
      for (x in this.addInfo) {
	for (v in this.addInfo[x]) {
	  if (x != "_:uri" && x != "http://www.openarchives.org/ore/terms/aggregates") {	    
	    createDataRow(newTable.id, x, this.addInfo[x][v]);
	  }
	}
      }
    }

    createRow(newTable.id);
  }
};


function finalizeRow(event) {
  row = parseInt(this.id.substring(6, this.id.length));
  val = document.getElementById('input_' + row);
  if (val) {
    // validate
    if (validate(val)) {
      par = val.parentNode;
      par.removeChild(val);
      if (val.valType == 'DatatypeProperty') {
	if (val.valRange  == 'http://www.w3.org/2001/XMLSchema#integer') {
	  v = val.value;
	} else {
	  v = "'" + val.value + "'";
	}
      } else {
	v = '<' + val.value + '>';
      }
      par.appendChild(document.createTextNode(v));
      row = document.getElementById('row_' + row);
      tab = row.parentNode.id
      createRow(tab);
    }
  }
}

function validate(input) {
  type = input.valRange;
  pt = input.valType;
  var par = input.parentNode;
  if (pt == 'ObjectProperty') {
    var reqv = createXMLHttpRequest();
    alertFunc = function() {
      if (reqv.readyState == 4) {
	info = eval('(' + reqv.responseText + ')');            
	par.removeChild(par.childNodes[0]);
	par.appendChild(document.createTextNode('<' + info['_:uri'] + '>'));

	// 'var_cell_' + current
	row = par.id.substring(9,par.id.length)
	img = document.getElementById('img_' + row);
	img.src = 'http://www.openannotation.org/adore-djatoka/images/forward.png';
	img.height = 24;
	img.width = 24;
	tr = document.getElementById('row_' + row);
	td = tr.childNodes[tr.childNodes.length -1];
	td.childNodes[td.childNodes.length-1].addInfo = info;
	td.childNodes[td.childNodes.length-1].value = info['_:uri'];


      }
    }
    reqv.onreadystatechange=alertFunc;
    url = "http://www.openannotation.org/shaman/sparql/triples?uri=" + input.value
    reqv.open("GET",url,true);
    reqv.send(null);
    row = par.id.substring(9,par.id.length);
    img = document.getElementById('img_' + row);
    img.src = 'http://www.openannotation.org/adore-djatoka/images/loading.gif';
    return 1;    
  }  
  if (type == "http://www.w3.org/2001/XMLSchema#dateTime") {
    ok = input.value.match(dateRe);
    if (!ok) {
      alert("That value needs to be a timestamp: YYYY-MM-DD HH:MM:SS");
      return 0;
    }
  } else if (type == "http://www.w3.org/2001/XMLSchema#integer") {
    pi = parseInt(input.value);
    if (pi == NaN) {
      alert("That value needs to be a number");
      return 0;
    }
  }
  return 1;
}

function newDOMDocument(rootTagName, namespaceURL) { 
	if (!rootTagName) rootTagName = ""; 
	if (!namespaceURL) namespaceURL = ""; 
	if (document.implementation && document.implementation.createDocument) { 
		// This is the W3C standard way to do it 
		return document.implementation.createDocument(namespaceURL, rootTagName, null); 
	} 
	else { 
		// This is the IE way to do it 
		// Create an empty document as an ActiveX object 
		// If there is no root element, this is all we have to do 
		var doc = new ActiveXObject("MSXML2.DOMDocument"); 
		// If there is a root tag, initialize the document 
		if (rootTagName) { 
			// Look for a namespace prefix 
			var prefix = ""; 
			var tagname = rootTagName; 
			var p = rootTagName.indexOf(':'); 
			if (p != -1) { 
		        prefix = rootTagName.substring(0, p); 
		        tagname = rootTagName.substring(p+1); 
		      } 
		      // If we have a namespace, we must have a namespace prefix 
		      // If we don't have a namespace, we discard any prefix 
		      if (namespaceURL) { 
		        if (!prefix) prefix = "a0"; // What Firefox uses 
		      } 
		      else prefix = ""; 
		      // Create the root element (with optional namespace) as a 
		      // string of text 
		      var text = "<" + (prefix?(prefix+":"):"") +  tagname + 
		          (namespaceURL 
		           ?(" xmlns:" + prefix + '="' + namespaceURL +'"') 
		           :"") + 
		          "/>"; 
		      // And parse that text into the empty document 
		      doc.loadXML(text); 
		} 
		return doc; 
	} 
};

	
function load(url){
	// Create a new document
	var xmldoc = this.newDOMDocument();
	xmldoc.asynch = false;
	xmldoc.load(url);
	return xmldoc;	
}

