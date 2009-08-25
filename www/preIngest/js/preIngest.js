XML_SCHEMA_STRING = 'http://www.w3.org/2001/XMLSchema#string';
XML_SCHEMA_DATETIME = 'http://www.w3.org/2001/XMLSchema#dateTime';

TYPE = 'type';
RANGE = 'range';
COMMENT = 'comment';

current = 0;
dateRe = new RegExp('[0-2][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]( [0-2][0-9]:[0-5][0-9]:[0-5][0-9])?');

dropDownHash = {};
treeNodeRdfInfoHash = {};

curResourceMapDOM = null;
tree1 = null;
selectedTreeNodeId = null;
latestNodeIDIncrement = -1;

//selectImgSrc = 'http://www.openannotation.org/adore-djatoka/images/forward.png';


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


// To-do: This is not finished yet
function sendPOSTResourceMap(url, func, xmlDoc) {
  req = createXMLHttpRequest();
  req.onreadystatechange=func;
  req.open("POST",null,true);
  req.file = xmlDoc;
  req.send(null);
  return false;
}

function queryClassOptions(what, selElem) {
  url = "http://localhost/preIngest/sparql/children/" + what;


  nf = function() {
    if (req.readyState==4 && req.status==200) {
      if (selElem.childNodes.length > 0) {
    	  return;
      }
      dropDownHash[TYPE] = {};
      dropDownHash[RANGE] = {};
      dropDownHash[COMMENT] = {};
      info = eval('(' + req.responseText + ')');            
      var opnElem = document.createElement('option');
      opnElem.value = ''
      opnElem.innerHTML = 'Select a Property...'
      selElem.appendChild(opnElem);	
      for (var i=0; i <info.length; i++) {
    	  var opnElem = document.createElement('option');
          nsLabel = info[i]['nsLabel'];
    	  opnElem.value = nsLabel;
    	  opnElem.innerHTML = info[i]['label'];
    	  dropDownHash[TYPE][nsLabel] = info[i]['propType'];
    	  dropDownHash[RANGE][nsLabel] = info[i][RANGE];
          dropDownHash[COMMENT][nsLabel] = info[i][COMMENT];
    	  selElem.appendChild(opnElem);	
      }	
    }
  }
  sendQuery(url, nf);
}

function queryObjectPropertyOptions(what, selElem) {
  url = "http://localhost/preIngest/sparql/children/" + what;

  nf = function() {
    if (req.readyState==4 && req.status==200) {
      if (selElem.childNodes.length > 0) {
    	  return;
      }
      dropDownHash[TYPE] = {};
      dropDownHash[RANGE] = {};
      dropDownHash[COMMENT] = {};
      info = eval('(' + req.responseText + ')');            
      var opnElem = document.createElement('option');
      opnElem.value = '';
      opnElem.innerHTML = 'Select a Class...';
      selElem.appendChild(opnElem);	
      for (var i=0; i <info.length; i++) {
    	  var opnElem = document.createElement('option');
    	  nsLabel = info[i]['nsLabel'];
    	  opnElem.value = nsLabel;
    	  opnElem.innerHTML = info[i]['label'];
    	  dropDownHash[TYPE][nsLabel] = 'Class';
    	  dropDownHash[RANGE][nsLabel] = null;
          dropDownHash[COMMENT][nsLabel] = info[i][COMMENT];
    	  selElem.appendChild(opnElem);	
      }	
    }
  }
  sendQuery(url, nf);
}

function queryObjectPropertyRangeOptions(what, selElem) {
  url = "http://localhost/preIngest/sparql/nodeInfo/" + what;

  nf = function() {
    if (req.readyState==4 && req.status==200) {
      if (selElem.childNodes.length > 0) {
    	  return;
      }
      dropDownHash[TYPE] = {};
      dropDownHash[RANGE] = {};
      dropDownHash[COMMENT] = {};
      info = eval('(' + req.responseText + ')');            
      var opnElem = document.createElement('option');
      opnElem.value = '';
      opnElem.innerHTML = 'Select a Class...';
      selElem.appendChild(opnElem);
      if (info.length > 0){
        var opnElem = document.createElement('option');
        nsLabel = info[0]['nsLabel'];
        opnElem.value = nsLabel;
        opnElem.innerHTML = info[0]['label'];
        dropDownHash[TYPE][nsLabel] = 'Class';
        dropDownHash[RANGE][nsLabel] = null;
        dropDownHash[COMMENT][nsLabel] = info[0][COMMENT];
        selElem.appendChild(opnElem);
      }
      else{
        opnElem.innerHTML = 'PYTHON-BUG: http://localhost/preIngest/sparql/nodeInfo/dcterms:Agent not working!'
        // To-do: fix this bug for dcterms:Agent
      }	
    }
  }
  sendQuery(url, nf);
}

function createClassOptionsList(rdfLabel) {
    var selectElem = document.createElement('select');
    selectElem.id = "sel1";    
       
    queryClassOptions(rdfLabel, selectElem); 
  
    selectElem.onchange = updateSelectDropDown;
    return selectElem;
}

function createObjectPropertyOptionsList(rdfLabel, rangeId) {
  var selectElem = document.createElement('select');
  selectElem.id = "sel1"; 
  
  if (rangeId){ 
        // A range specified for this node, so get al 
        queryObjectPropertyRangeOptions(rangeId, selectElem); 	
  }else{
        // No range specified for this node, so get all possible children of the current node
        queryObjectPropertyOptions(rdfLabel, selectElem); 
  }
  
  selectElem.onchange = updateSelectDropDown;
  return selectElem;
}

function createDataTypeStringInput(value) {
  //Display the text box with value 
  var inputElem = document.createElement('input');
  inputElem.id = "inputString1";
  inputElem.type="text";
  inputElem.value = value; 
  
  return inputElem;
}

function createDataTypeDateTimeInput(value){


}

function deleteRows(tabl) {
    for(var i = tabl.rows.length; i > 0;i--){
        tabl.deleteRow(i -1);
    }
}

function updateNodeDetailPanel() {
    tab = document.getElementById('nodeDetailTable');
    //delete the old details
    if (tab.childNodes.length > 0) {
        deleteRows(tab);
    }

    // Create the row for Node Name
	var tr1 = document.createElement('tr');
	var td11 = document.createElement('td');
    var td12 = document.createElement('td');
    var txtNodeNameTitle = document.createElement('p');
    txtNodeNameTitle.class = 'textLabel';
    txtNodeNameTitle.innerHTML = 'Node Label: ';
    var txtNodeNameValue = document.createElement('p');
    txtNodeNameValue.class = 'textValue';
    txtNodeNameValue.innerHTML = getRDFLabel(selectedTreeNodeId);

    td11.appendChild(txtNodeNameTitle);
    td12.appendChild(txtNodeNameValue);
    tr1.appendChild(td11);
    tr1.appendChild(td12);
    tab.appendChild(tr1);
    

    // Create the row for Node Type
	var tr2 = document.createElement('tr');
	var td21 = document.createElement('td');
    var td22 = document.createElement('td');
    var txtNodeTypeTitle = document.createElement('p');
    txtNodeTypeTitle.class = 'textLabel';
    txtNodeTypeTitle.innerHTML = 'Node Type: ';
    var txtNodeTypeValue = document.createElement('p');
    txtNodeTypeValue.class = 'textValue';
    txtNodeTypeValue.innerHTML = treeNodeRdfInfoHash[selectedTreeNodeId][TYPE];

    td21.appendChild(txtNodeTypeTitle);
    td22.appendChild(txtNodeTypeValue);
    tr2.appendChild(td21);
    tr2.appendChild(td22);
    tab.appendChild(tr2);
    
   
    // Create the row for Node Description
	var tr3 = document.createElement('tr');
	var td3 = document.createElement('td');
    var tr4 = document.createElement('tr');
    var td4 = document.createElement('td');
    var txtNodeDescrTitle = document.createElement('p');
    txtNodeDescrTitle.class = 'textLabel';
    txtNodeDescrTitle.innerHTML = 'Node Description: ';
    var txtNodeDescrValue = document.createElement('p');
    txtNodeDescrValue.class = 'textMemo';
    txtNodeDescrValue.innerHTML = treeNodeRdfInfoHash[selectedTreeNodeId][COMMENT];

    td3.appendChild(txtNodeDescrTitle);
    td4.appendChild(txtNodeDescrValue);
    tr3.appendChild(td3);
    tr4.appendChild(td4);
    tab.appendChild(tr3); 
    tab.appendChild(tr4);    
}

function updateAddNodePanel() {
    // get selected node id and type/range info
    rdfLabel = getRDFLabel(selectedTreeNodeId);
    rdfType = treeNodeRdfInfoHash[selectedTreeNodeId][TYPE];
    rdfRange = treeNodeRdfInfoHash[selectedTreeNodeId][RANGE];
    
    // delete the form's select elements
    tab = document.getElementById('editNodeTable');
        
    //delete the old options
    if (tab.childNodes.length > 0) {
        deleteRows(tab);
    }    
    
    // Create the row for new options
	var tr1 = document.createElement('tr');
	var td1 = document.createElement('td');

    // Create the row for drop-down info Text box
    var tr2 = document.createElement('tr');
    var td2 = document.createElement('td');
    
    //Create display for RDF:comments about the selected drop-down item
    var textPara = document.createElement('p');
    textPara.class = 'textMemo';
    textPara.id = 'dropDownOptDescription';
    
    // Create the row for submit/delete buttons
    var tr3 = document.createElement('tr');
    var td3 = document.createElement('td');

    //.....eg ...<button name="subject" type="submit" value="HTML">HTML</button>
    var btn = document.createElement('input');
    btn.type = 'button';
    btn.id = 'editNodeButton';
    btn.value = 'Add';

    switch (rdfType)
    {
        case 'DatatypeProperty':
            //Create a input text box and populate with value if exists

            //...Get Value if one already exists
            childNodeVal = getChildTreeNodeDatatypeValue(selectedTreeNodeId);
            switch (rdfRange)
            {   
                case XML_SCHEMA_STRING:               
	                td1.appendChild(createDataTypeStringInput(childNodeVal));
                    if(childNodeVal){
                        btn.value = 'Update'
                        btn.onclick = updateLeafNodeFromStringDataType;
                    }else{
                        btn.onclick = addNewNodeFromStringDataType;
                    }                    
                    break;
                case XML_SCHEMA_DATETIME:
                    td1.appendChild(createDataTypeDateTimeInput(childNodeVal));
                    if(childNodeVal){
                        btn.value = 'Update'
                        btn.onclick = updateLeafNodeFromDateTimeDataType;
                    }else{
                        btn.onclick = addNewNodeFromDateTimeDataType;
                    }  
                    break;
                default:
                    //alert("Unknown Type associated with selected Datatype node: " + rdfRange); 
            }  
            break; 
        case 'simple': //Leaf node (simple data type)
            //Create a input text box and populate with value if exists
            //...Get Value if one already exists
            value = getTreeNodeDatatypeValue(selectedTreeNodeId);
            if(value){
                btn.value = 'Update'
            }     
            switch (rdfRange)
            {           
                case XML_SCHEMA_STRING:
                    //Get Value if one already exists
	                td1.appendChild(createDataTypeStringInput(value));
                    btn.onclick = updateLeafNodeFromStringDataType;
                    break;
                case XML_SCHEMA_DATETIME:
                    //Get Value if one already exists
                    td1.appendChild(createDataTypeDateTimeInput(value));
                    btn.onclick = updateLeafNodeFromDateTimeDataType;
                    break;
                default:
                    //alert("Unknown Type associated with selected Datatype node: " + rdfRange); 
            }  
            break;
        case 'ObjectProperty':
        // NOTE:  This doesn't work in firefox 2.x, rows not updated dynamically
            td1.appendChild(createObjectPropertyOptionsList(rdfLabel, rdfRange));
            btn.onclick = addNewNodeFromDropDown;
            break;
        case 'Class':
            td1.appendChild(createClassOptionsList(rdfLabel, rdfRange));
            btn.onclick = addNewNodeFromDropDown;
            break;                    
        default:
           //alert("Incorrect RDF Type associated with selected node: " + rdfType);     
    }

    tr1.appendChild(td1);
	tab.appendChild(tr1);

    td2.appendChild(textPara);
    tr2.appendChild(td2);
    tab.appendChild(tr2);
    
    td3.appendChild(btn);
    tr3.appendChild(td3);
    tab.appendChild(tr3); 
}

function addNewNodeFromDropDown(event){
  // Get the info for the selected item on the drop down menu
  sel = document.getElementById('sel1');
  
  if(sel.selectedIndex > 0){
    var opt = sel.options[sel.selectedIndex];
    val = opt.value;  
    dt = dropDownHash[TYPE][val];
    rng = dropDownHash[RANGE][val];
    cmt = dropDownHash[COMMENT][val];

    // Add the selected item type to the selected node of the treeview.  
    addTreeNode(selectedTreeNodeId, getNewNodeId(val), opt.innerHTML, true, dt, rng, cmt);
  }    
}

function addNewNodeFromStringDataType(event){
  var inputElem = document.getElementById("inputString1");
  str = inputElem.value;
  
  // Add the selected item type to the selected node of the treeview.  
  addTreeNode(selectedTreeNodeId, getNewNodeId(XML_SCHEMA_STRING), str, true, 'simple', XML_SCHEMA_STRING,
        'Basic string value');    
}

function addNewNodeFromDateTimeDataType(event){
  var inputElem = document.getElementById("inputDateTime1");
  dateTime = "";

  // Add the selected item type to the selected node of the treeview.  
  addTreeNode(selectedTreeNodeId, getNewNodeId(XML_SCHEMA_DATETIME), dateTime, true, 'simple', XML_SCHEMA_DATETIME, 'Basic date/time value');    
}

function updateLeafNodeFromStringDataType(event){
  var inputElem = document.getElementById("inputString1");
  str = inputElem.value;
    
  tbl = getNodesChildTable(selectedTreeNodeId);
  if (tbl) {
    aElem = tbl.getElementsByTagName("a")[0];
  }else{
    tbl = getNodesTable(selectedTreeNodeId);
    aElem = tbl.getElementsByTagName("a")[0];
  }
  aElem.innerHTML = str;   
}

function updateLeafNodeFromDateTimeDataType(event){
  var inputElem = document.getElementById("inputDateTime1");
  dateTime = inputElem.value;
    
  tbl = getNodesChildTable(selectedTreeNodeId);
  if (tbl) {
    aElem = tbl.getElementsByTagName("a")[0];
  }else{
    tbl = getNodesTable(selectedTreeNodeId);
    aElem = tbl.getElementsByTagName("a")[0];
  }
  aElem.innerHTML = dateTime;         
}

////////////////////////////////////////////////////////
////////////////////////////////////////////////////////

function loadRicoTree(xmlFileName){
	Rico.loadModule('Tree');
	
	Rico.onLoad( function() {
  	// initialize tree
  	var options={
    	  showCheckBox : false,
    	  showLines    : true,
    	  showPlusMinus: true,
    	  showFolders  : true,
          defaultAction: this.updateSelectedTreeNodeHandler.bindAsEventListener(this),
  	}
	tree1=new Rico.TreeControl("tree1", null, options);    

	tree1.setTreeDiv('tree1');

	// add RootNode
    // To-do: below is a bit of a hack, just to get an initail comment, without
    //        having to make a call to the server. + a more user friendly version
    //        might be required.
    oreRMComment = 'A description of and Aggregation accordcing to the OAI-ORE data model.';
    
	newTreeNode = addTreeNode(null,'ore:ResourceMap','Resource-Map',true, 'Class', null, oreRMComment);
    updateSelectedTreeNode(newTreeNode);
	// open tree
  	tree1.open();
	});
}

function addTreeNode(parentId, nodeId, desc, isContainer, rdfType, rdfRange, rdfComment){
    tree1.addNode(parentId, nodeId, desc, isContainer, 1, null, null);
    treeNodeRdfInfoHash[nodeId] = {};
    treeNodeRdfInfoHash[nodeId][TYPE] = rdfType;
    treeNodeRdfInfoHash[nodeId][RANGE] = rdfRange;
    treeNodeRdfInfoHash[nodeId][COMMENT] = rdfComment;

    // To-do: Open the parent tree node so it displays all children    
    
    return document.getElementById(tree1.domID(nodeId, 'Desc'));
}

function updateSelectedTreeNodeHandler(e){ 
    // assert: eventNode = the nodes <a> / 'Desc' element
    var eventNode = Event.element(e);    
    updateSelectedTreeNode(eventNode);     
}

function updateSelectedTreeNode(node){
    // assert: node = the nodes <a> / 'Desc' element
    selectedTreeNodeId = getTreeIdFromDOMId(node.id);
    updateAddNodePanel();
    updateNodeDetailPanel();

    // To-do: Make the selected tree node bold or different colour    
}

function getRDFLabel(treeId){
    treeIdSplit = treeId.split('-');
    return treeIdSplit[0];
}

function getChildTreeNodeDatatypeValue(nodeId){
    childTable = getNodesChildTable(nodeId);
    if (childTable){
        aElem = childTable.getElementsByTagName("a")[0];
        return aElem.innerHTML; 
    }
    else
    {   
        return null;    
    }  
}

function getTreeNodeDatatypeValue(nodeId){
    table = getNodesTable(nodeId);
    if (table){
        aElem = table.getElementsByTagName("a")[0];
        return aElem.innerHTML; 
    }
    else
    {   
        return null;    
    }     
}

function getNodesChildDiv(nodeId){
    childrenDiv = document.getElementById(tree1.domID(nodeId, 'Children'));
    childDiv = childrenDiv.getElementsByTagName('div')[0];
    return childDiv;
}

function getNodesChildTable(nodeId){
    childrenDiv = document.getElementById(tree1.domID(nodeId, 'Children'));
    childTable = childrenDiv.getElementsByTagName('table')[0];
    return childTable;
}


function getNodesTable(nodeId){
    return document.getElementById(tree1.domID(nodeId, 'Parent'));
}

function getTreeIdFromDOMId(domId){
    idSplit = domId.split('_');
    return idSplit[idSplit.length-1];
}

function updateSelectDropDown(event) {
  // update the info display for the current selected drop-down item

  // Get the info for the selected item on the drop down menu
 
  if(this.selectedIndex > 0){
    var opt = this.options[this.selectedIndex];
    val = opt.value;  
    
    textBox = document.getElementById('dropDownOptDescription');
    newDescr = dropDownHash[COMMENT][val];
    textBox.innerHTML = newDescr;
  }
}

function updateDataTypeText(event){
  // Get the info for the selected item on the drop down menu
  txt = document.getElementById('text1');
  val = txt.val;  

  // Add the selected item type to the selected node of the treeview.  
  addTreeNode(selectedTreeNodeId, getNewNodeId(val), txt.innerHTML, true, XML_SCHEMA_STRING, null);    
}

function getNewNodeId(textId){
    // To-do: Need to improve this to handle
    //   tree's that have been re-loaded and don't start at 0
    latestNodeIDIncrement = latestNodeIDIncrement + 1; 
    return textId + '-' + latestNodeIDIncrement; 
}
