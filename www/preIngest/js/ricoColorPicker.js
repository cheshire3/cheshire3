// ===================================================================
// Original author: Matt Kruse <matt@mattkruse.com>
// WWW: http://www.mattkruse.com/
//
// Adapted to Rico by Matt Brown
// ===================================================================


Rico.ColorPicker = Class.create(
/** @lends Rico.ColorPicker# */
{
/**
 * @class Implements a pop-up color picker control.
 * @extends Rico.Popup
 * @constructs
 * @param id unique identifier
 * @param options object may contain any of the following:<dl>
 *   <dt>showColorCode</dt><dd> show hex color code as user hovers over color grid? default=false</dd>
 *   <dt>cellsPerRow  </dt><dd> number of colors per row in the grid? default=18</dd>
 *   <dt>palette      </dt><dd> array of 6 digit hex values, default=216 "web safe" colors</dd>
 *</dl>
 */
  initialize: function(id,options) {
    this.id=id;
    this.currentValue = "#FFFFFF";
    Object.extend(this, new Rico.Popup());
    Object.extend(this.options, {
      showColorCode : false,
      cellsPerRow   : 18,
      palette       : []
    });
    var hexvals=['00','33','66','99','CC','FF'];
    for (var g=0; g<hexvals.length; g++) {
      for (var r=0; r<hexvals.length; r++) {
        for (var b=0; b<hexvals.length; b++) {
          this.options.palette.push(hexvals[r]+hexvals[g]+hexvals[b]);
        }
      }
    }
    Object.extend(this.options, options || {});
  },

  atLoad : function() {
    this.container=document.createElement("div");
    this.container.style.display="none";
    this.container.className='ricoColorPicker';
    var width = this.options.cellsPerRow;
    var cp_contents = "<TABLE BORDER='1' CELLSPACING='1' CELLPADDING='0'>";
    for (var i=0; i<this.options.palette.length; i++) {
      if ((i % width) == 0) { cp_contents += "<TR>"; }
      cp_contents += '<TD BGCOLOR="#'+this.options.palette[i]+'">&nbsp;</TD>';
      if ( ((i+1)>=this.options.palette.length) || (((i+1) % width) == 0)) {
        cp_contents += "</TR>";
      }
    }
    var halfwidth = Math.floor(width/2);
    if (this.options.showColorCode) {
      cp_contents += "<TR><TD COLSPAN='"+halfwidth+"' ID='colorPickerSelectedColor'>&nbsp;</TD><TD COLSPAN='"+(width-halfwidth)+"' ALIGN='CENTER' ID='colorPickerSelectedColorValue'>#FFFFFF</TD></TR>";
    } else {
      cp_contents += "<TR><TD COLSPAN='"+width+"' ID='colorPickerSelectedColor'>&nbsp;</TD></TR>";
    }
    cp_contents += "</TABLE>";
    this.container.innerHTML=cp_contents;
    document.body.appendChild(this.container);
    this.setDiv(this.container);
    /**
     * alias for openPopup
     * @function
     */
    this.open=this.openPopup;
    /**
     * alias for closePopup
     * @function
     */
    this.close=this.closePopup;
    Event.observe(this.container,"mouseover", this.highlightColor.bindAsEventListener(this), false);
    Event.observe(this.container,"click", this.selectColor.bindAsEventListener(this), false);
    this.close();
  },

/** @private */
  selectColor: function(e) {
    Event.stop(e);
    if (this.returnValue) this.returnValue(this.currentValue);
    this.close();
  },

/* This function runs when you move your mouse over a color block */
/** @private */
  highlightColor: function(e) {
    var elem = Event.element(e);
    if (!elem.tagName || elem.tagName.toLowerCase() != 'td') return;
    var c=Rico.Color.createColorFromBackground(elem).toString();
    this.currentValue = c;
    Element.setStyle('colorPickerSelectedColor', {backgroundColor:c}, true);
    var d = $("colorPickerSelectedColorValue");
    if (d) d.innerHTML = c;
  }
});

Rico.includeLoaded('ricoColorPicker.js');
