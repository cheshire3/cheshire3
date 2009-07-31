/*
 *  Rico.Buffer.AjaxJSON
 *
 *  JSON handling code for the Rico Live Grid written by
 *  Jeremy Green.  Adapted from code by Richard Cowin
 *  and Matt Brown.
 *
 *  (c) 2005-2009 Richard Cowin (http://openrico.org)
 *  (c) 2005-2009 Matt Brown (http://dowdybrown.com)
 *  (c) 2008-2009 Jeremy Green (http://www.webEprint.com)
 *
 *  Rico is licensed under the Apache License, Version 2.0 (the "License"); you may not use this
 *  file except in compliance with the License. You may obtain a copy of the License at
 *
 *         http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software distributed under the
 *  License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 *  either express or implied. See the License for the specific language governing permissions
 *  and limitations under the License.
 */


Rico.Buffer.AjaxJSON = Class.create(
/** @lends Rico.Buffer.AjaxJSON# */
{
/**
 * @class Implements a LiveGrid buffer that can make
  *  AJAX calls to the server and process responses in
  *  JSON format.  Extended from Rico.Buffer.AjaxSQL.
  *
  *  @example
  *  Data format:
  *  The data consumed by this buffer should be a JavaScript
  *  hash type object.  The format closely follows the XML based
  *  data consumed by the Rico.Buffer.AjaxSQL buffer.
  *
  *  {
  *  "update_ui":true,
  *  "offset":0,
  *  "rowCount":20,
  *  "rows":[
  *     ["1","Bob"],
  *     ["2","Bill"]
  *   ]
  *  }
  *
  *  The 'rows' value object of the data object is
  *  a normal JS Array with each element also being an array.
  *
  *
  *  @example
  *  Example Usage:
  *  buffer=new Rico.Buffer.AjaxJSON(jsonUrl, bufferopts);
  *
  *  jsonUrl should return a string in the above format.  It will
  *  be parsed into JS objects.
  *
 * @extends Rico.Buffer.AjaxSQL
 * @constructs
 */
initialize: function(url,options,ajaxOptions) {
  Object.extend(this, new Rico.Buffer.AjaxSQL());
  Object.extend(this, new Rico.Buffer.AjaxJSONMethods());
  this.dataSource=url;
  Object.extend(this.options, options || {});
  Object.extend(this.ajaxOptions, ajaxOptions || {});
}

});



Rico.Buffer.AjaxJSONMethods = function() {};

Rico.Buffer.AjaxJSONMethods.prototype = {
/** @lends Rico.Buffer.AjaxJSON# */

processResponse: function(startPos,request) {
  var json = request.responseText.evalJSON(true);
  if (!json || json == null) {
    Rico.writeDebugMsg("jsonAjaxUpdate: json conversion failed");
    return false;
  }

  if (json.debug) {
    for (var i=0; i<json.debug.length; i++)
      Rico.writeDebugMsg("debug msg "+i+": "+json.debug[i]);
  }
  if (json.error) {
    alert("Data provider returned an error:\n"+json.error);
    Rico.writeDebugMsg("Data provider returned an error:\n"+json.error);
    return false;
  }

  this.rcvdRows = 0;
  var newRows = this.loadRows(json);
  if (newRows==null) return false;
  this.rcvdRows = newRows.length;

  this.updateBuffer(startPos, newRows);
  return true;
},

loadRows: function(json) {
  Rico.writeDebugMsg("loadRows");
  json = $H(json);
  this.rcvdRowCount = false;
  var rowsElement = json.get("rows");
  var rowcnt = json.get("rowCount");

  if (rowcnt) {
    this.rowcntContent = rowcnt;
    this.rcvdRowCount = true;
    this.foundRowCount = true;
    Rico.writeDebugMsg("loadRows, found RowCount="+this.rowcntContent);
  }
  this.updateUI = json.get("update_ui");
  this.rcvdOffset = json.get("offset");
  Rico.writeDebugMsg("loadRows, rcvdOffset="+this.rcvdOffset);
  if (this.options.template)
    return this.template2jsTable(json,this.options.template);
  else
    return rowsElement;
    //return this.json2jsTable(json);
},

json2jsTable: function(json,firstRow) {
  var newRows = new Array();
  var trs = json.get("rows");
  trs = $A(trs);
  var i = 0;
  var acceptAttr=this.options.acceptAttr;
  trs.each(function(rowData){
    var row = new Array();
    //var rowData = $H(pair.value);
    rowData = $H(rowData);
    var j = 0;
    rowData.each(function(p2){
      row[j]={};
      row[j].content=p2.value;
      for (var k=0; k<acceptAttr.length; k++)
        row[j]['_'+acceptAttr[k]]="";
      j++;
    });
    newRows.push( row );
    i++;
  });
  return newRows;
},

template2jsTable: function(json,template){
  var trs = json.get("rows");
  trs = $A(trs);
  var rowsString = '<table>';
  trs.each(function(rowData){
    rowsString += template.evaluate(rowData);
  });
  rowsString += '</table>';
  var rowDom = this.string2DOM(rowsString);
  return this.dom2jstable(rowDom);
},

string2DOM: function(string){
  var xmlDoc = null;
  try{ //Internet Explorer
    xmlDoc=new ActiveXObject("Microsoft.XMLDOM");
    xmlDoc.async="false";
    xmlDoc.loadXML(string);
  } catch(e) {
    try { //Firefox, Mozilla, Opera, etc.
      var parser=new DOMParser();
      xmlDoc=parser.parseFromString(string,"text/xml");
    } catch(e) {
      alert(e.message);
    }
  }
  var el = document._importNode(xmlDoc.childNodes[0],true);
  return el;
}

};

Rico.includeLoaded('ricoLiveGridJSON.js');
