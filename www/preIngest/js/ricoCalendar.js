//  By Matt Brown
//  June-October 2006
//  email: dowdybrown@yahoo.com
//  Inspired by code originally written by Tan Ling Wee on 2 Dec 2001
//  Requires prototype.js and ricoCommon.js

Rico.CalendarControl = Class.create(
/** @lends Rico.CalendarControl# */
{
/**
 * @class Implements a pop-up Gregorian calendar.
 * Dates of adoption of the Gregorian calendar vary by country - accurate as a US & British calendar from 14 Sept 1752 to present.
 * Mark special dates with calls to addHoliday()
 * @extends Rico.Popup
 * @constructs
 * @param id unique identifier
 * @param options object may contain any of the following:<dl>
 *   <dt>startAt       </dt><dd> week starts with 0=sunday, 1=monday? default=0</dd>
 *   <dt>showWeekNumber</dt><dd> show week number in first column? default=0</dd>
 *   <dt>showToday     </dt><dd> show "Today is..." in footer? default=1</dd>
 *   <dt>cursorColor   </dt><dd> color used to highlight dates as the user moves their mouse, default=#FDD</dd>
 *   <dt>repeatInterval</dt><dd> when left/right arrow is pressed, repeat action every x milliseconds, default=100</dd>
 *   <dt>dateFmt       </dt><dd> date format for return value (one of values accepted by {@link Date#formatDate}), default=ISO8601</dd>
 *   <dt>selectedDateBorder</dt><dd> border to indicate currently selected date? default=#666666</dd>
 *   <dt>minDate       </dt><dd> earliest selectable date? default=today-50 years</dd>
 *   <dt>maxDate       </dt><dd> last selectable date? default=today+50 years</dd>
 *</dl>
 */
  initialize: function(id,options) {
    this.id=id;
    var today=new Date();
    Object.extend(this, new Rico.Popup({ignoreClicks:true}));
    Object.extend(this.options, {
      startAt : 0,
      showWeekNumber : 0,
      showToday : 1,
      cursorColor: '#FDD',
      repeatInterval : 100,
      dateFmt : 'ISO8601',
      selectedDateBorder : "#666666",
      minDate : new Date(today.getFullYear()-50,0,1),
      maxDate : new Date(today.getFullYear()+50,11,31)
    });
    Object.extend(this.options, options || {});
    /**
     * alias for closePopup
     * @function
     */
    this.close=this.closePopup;
    this.bPageLoaded=false;
    this.img=[];
    this.Holidays={};
    this.weekString=RicoTranslate.getPhraseById("calWeekHdg");
    this.re=/^\s*(\w+)(\W)(\w+)(\W)(\w+)/i;
    this.setDateFmt(this.options.dateFmt);
  },


  setDateFmt: function(fmt) {
    this.dateFmt=(fmt=='rico') ? RicoTranslate.dateFmt : fmt;
    this.dateParts=[];
    if (this.re.exec(this.dateFmt)) {
      this.dateParts[RegExp.$1]=0;
      this.dateParts[RegExp.$3]=1;
      this.dateParts[RegExp.$5]=2;
    }
  },
  
/**
 * Call before displaying calendar to highlight special days
 * @param d day (1-31)
 * @param m month (1-12)
 * @param y year (0 implies a repeating holiday)
 * @param desc description
 * @param bgColor background color for cell displaying this day (CSS value, defaults to '#DDF')
 * @param txtColor text color for cell displaying this day (CSS value), if not specified it is displayed with the same color as other days
 */
  addHoliday : function(d, m, y, desc, bgColor, txtColor) {
    this.Holidays[this.holidayKey(y,m-1,d)]={desc:desc, txtColor:txtColor, bgColor:bgColor || '#DDF'};
  },
  
/** @private */
  holidayKey : function(y,m,d) {
    return 'h'+y.toPaddedString(4)+m.toPaddedString(2)+d.toPaddedString(2);
  },

  atLoad : function() {
    this.container=document.createElement("div");
    this.container.style.display="none";
    this.container.id=this.id;
    this.container.className='ricoCalContainer';

    this.maintab=document.createElement("table");
    this.maintab.cellSpacing=0;
    this.maintab.cellPadding=0;
    this.maintab.border=0;
    this.maintab.className='ricoCalTab';

    var r,c,i,j,img,dow,a,s;
    for (i=0; i<7; i++) {
      r=this.maintab.insertRow(-1);
      r.className='row'+i;
      for (c=0; c<8; c++) {
        r.insertCell(-1);
      }
    }
    this.tbody=this.maintab.tBodies[0];
    r=this.tbody.rows[0];
    r.className='ricoCalDayNames';
    if (this.options.showWeekNumber) {
      r.cells[0].innerHTML=this.weekString;
      for (i=0; i<7; i++) {
        this.tbody.rows[i].cells[0].className='ricoCalWeekNum';
      }
    }
    this.styles=[];
    for (i=0; i<7; i++) {
      dow=(i+this.options.startAt) % 7;
      r.cells[i+1].innerHTML=RicoTranslate.dayAbbr(dow);
      this.styles[i+1]='ricoCal'+dow;
    }
    
    // table header (navigation controls)
    this.thead=this.maintab.createTHead();
    r=this.thead.insertRow(-1);
    c=r.insertCell(-1);
    c.colSpan=8;
    img=this.createNavArrow('decMonth','left');
    c.appendChild(document.createElement("a")).appendChild(img);
    this.titleMonth=document.createElement("a");
    c.appendChild(this.titleMonth);
    Event.observe(this.titleMonth,"click", this.popUpMonth.bindAsEventListener(this), false);
    img=this.createNavArrow('incMonth','right');
    c.appendChild(document.createElement("a")).appendChild(img);
    s=document.createElement("span");
    s.innerHTML='&nbsp;';
    s.style.paddingLeft='3em';
    c.appendChild(s);

    img=this.createNavArrow('decYear','left');
    c.appendChild(document.createElement("a")).appendChild(img);
    this.titleYear=document.createElement("a");
    Event.observe(this.titleYear,"click", this.popUpYear.bindAsEventListener(this), false);
    c.appendChild(this.titleYear);
    img=this.createNavArrow('incYear','right');
    c.appendChild(document.createElement("a")).appendChild(img);

    // table footer (today)
    if (this.options.showToday) {
      this.tfoot=this.maintab.createTFoot();
      r=this.tfoot.insertRow(-1);
      this.todayCell=r.insertCell(-1);
      this.todayCell.colSpan=8;
      Event.observe(this.todayCell,"click", this.selectNow.bindAsEventListener(this), false);
    }
    

    this.container.appendChild(this.maintab);
    
    // close icon (upper right)
    img=document.createElement("img");
    img.src=Rico.imgDir+'close.gif';
    img.onclick=this.close.bind(this);
    img.style.cursor='pointer';
    img.style.position='absolute';
    img.style.top='1px';   /* assumes a 1px border */
    img.style.right='1px';
    img.title=RicoTranslate.getPhraseById('close');
    this.container.appendChild(img);
    
    // month selector
    this.monthSelect=document.createElement("table");
    this.monthSelect.className='ricoCalMenu';
    this.monthSelect.cellPadding=2;
    this.monthSelect.cellSpacing=0;
    this.monthSelect.border=0;
    for (i=0; i<4; i++) {
      r=this.monthSelect.insertRow(-1);
      for (j=0; j<3; j++) {
        c=r.insertCell(-1);
        a=document.createElement("a");
        a.innerHTML=RicoTranslate.monthAbbr(i*3+j);
        a.name=i*3+j;
        c.appendChild(a);
        Event.observe(a,"click", this.selectMonth.bindAsEventListener(this), false);
      }
    }
    this.monthSelect.style.display='none';
    this.container.appendChild(this.monthSelect);
    
    // year selector
    this.yearPopup=document.createElement("div");
    this.yearPopup.style.display="block";
    this.yearPopup.className='ricoCalYearPrompt';
    this.container.appendChild(this.yearPopup);
    this.yearPopupSpan=this.yearPopup.appendChild(document.createElement("span"));
    this.yearPopupYear=this.yearPopup.appendChild(document.createElement("input"));
    this.yearPopupYear.maxlength=4;
    this.yearPopupYear.size=4;
    Event.observe(this.yearPopupYear,"keypress", this.yearKey.bindAsEventListener(this), false);

    img=document.createElement("img");
    img.src=Rico.imgDir+'checkmark.gif';
    Event.observe(img,"click", this.processPopUpYear.bindAsEventListener(this), false);
    this.yearPopup.appendChild(img);

    img=document.createElement("img");
    img.src=Rico.imgDir+'delete.gif';
    Event.observe(img,"click", this.popDownYear.bindAsEventListener(this), false);
    this.yearPopup.appendChild(img);
    
    // fix anchors so they work in IE6
    a=this.container.getElementsByTagName('a');
    for (i=0; i<a.length; i++) {
      a[i].href='javascript:void(0)';
    }
    
    Event.observe(this.tbody,"click", this.saveAndClose.bindAsEventListener(this));
    Event.observe(this.tbody,"mouseover", this.mouseOver.bindAsEventListener(this));
    Event.observe(this.tbody,"mouseout",  this.mouseOut.bindAsEventListener(this));
    document.getElementsByTagName("body")[0].appendChild(this.container);
    this.setDiv(this.container);
    this.close();
    this.bPageLoaded=true;
  },
  
  selectNow : function() {
    this.monthSelected=this.monthNow;
    this.yearSelected=this.yearNow;
    this.constructCalendar();
  },
  
/** @private */
  createNavArrow: function(funcname,gifname) {
    var img=document.createElement("img");
    img.src=Rico.imgDir+gifname+'.gif';
    img.name=funcname;
    Event.observe(img,"click", this[funcname].bindAsEventListener(this), false);
    Event.observe(img,"mousedown", this.mouseDown.bindAsEventListener(this), false);
    Event.observe(img,"mouseup", this.mouseUp.bindAsEventListener(this), false);
    Event.observe(img,"mouseout", this.mouseUp.bindAsEventListener(this), false);
    return img;
  },

/** @private */
  mouseOver: function(e) {
    var el=Event.element(e);
    if (this.lastHighlight==el) return;
    this.unhighlight();
    var s=el.innerHTML.replace(/&nbsp;/g,'');
    if (s=='' || el.className=='ricoCalWeekNum') return;
    var day=parseInt(s,10);
    if (isNaN(day)) return;
    this.lastHighlight=el;
    this.tmpColor=el.style.backgroundColor;
    el.style.backgroundColor=this.options.cursorColor;
  },
  
/** @private */
  unhighlight: function() {
    if (!this.lastHighlight) return;
    this.lastHighlight.style.backgroundColor=this.tmpColor;
    this.lastHighlight=null;
  },
  
/** @private */
  mouseOut: function(e) {
    var el=Event.element(e);
    if (el==this.lastHighlight) this.unhighlight();
  },
  
/** @private */
  mouseDown: function(e) {
    var el=Event.element(e);
    this.repeatFunc=this[el.name].bind(this);
    this.timeoutID=setTimeout(this.repeatStart.bind(this),500);
  },
  
/** @private */
  mouseUp: function(e) {
    clearTimeout(this.timeoutID);
    clearInterval(this.intervalID);
  },
  
/** @private */
  repeatStart : function() {
    clearInterval(this.intervalID);
    this.intervalID=setInterval(this.repeatFunc,this.options.repeatInterval);
  },
  
/**
 * @returns true if yr/mo is within minDate/MaxDate
 */
  isValidMonth : function(yr,mo) {
    if (yr < this.options.minDate.getFullYear()) return false;
    if (yr == this.options.minDate.getFullYear() && mo < this.options.minDate.getMonth()) return false;
    if (yr > this.options.maxDate.getFullYear()) return false;
    if (yr == this.options.maxDate.getFullYear() && mo > this.options.maxDate.getMonth()) return false;
    return true;
  },

  incMonth : function() {
    var newMonth=this.monthSelected+1;
    var newYear=this.yearSelected;
    if (newMonth>11) {
      newMonth=0;
      newYear++;
    }
    if (!this.isValidMonth(newYear,newMonth)) return;
    this.monthSelected=newMonth;
    this.yearSelected=newYear;
    this.constructCalendar();
  },

  decMonth : function() {
    var newMonth=this.monthSelected-1;
    var newYear=this.yearSelected;
    if (newMonth<0) {
      newMonth=11;
      newYear--;
    }
    if (!this.isValidMonth(newYear,newMonth)) return;
    this.monthSelected=newMonth;
    this.yearSelected=newYear;
    this.constructCalendar();
  },
  
/** @private */
  selectMonth : function(e) {
    var el=Event.element(e);
    this.monthSelected=parseInt(el.name,10);
    this.constructCalendar();
    Event.stop(e);
  },

  popUpMonth : function() {
    Element.toggle(this.monthSelect);
    this.monthSelect.style.top=(this.thead.offsetHeight+2)+'px';
    this.monthSelect.style.left=this.titleMonth.offsetLeft+'px';
  },

  popDownMonth : function() {
    Element.hide(this.monthSelect);
  },

  popDownYear : function() {
    Element.hide(this.yearPopup);
    this.yearPopup.disabled=true;  // make sure this does not get submitted
  },

/**
 * Prompt for year
 */
  popUpYear : function() {
    Element.toggle(this.yearPopup);
    if (!Element.visible(this.yearPopup)) return;
    this.yearPopup.disabled=false;
    this.yearPopup.style.left='120px';
    this.yearPopup.style.top=(this.thead.offsetHeight+2)+'px';
    this.yearPopupSpan.innerHTML='&nbsp;'+RicoTranslate.getPhraseById("calYearRange",this.options.minDate.getFullYear(),this.options.maxDate.getFullYear())+'<br>';
    this.yearPopupYear.value='';   // this.yearSelected
    this.yearPopupYear.focus();
  },
  
  yearKey : function(e) {
    switch (RicoUtil.eventKey(e)) {
      case 27: this.popDownYear(); Event.stop(e); return false;
      case 13: this.processPopUpYear(); Event.stop(e); return false;
    }
    return true;
  },
  
  processPopUpYear : function() {
    var newYear=this.yearPopupYear.value;
    newYear=parseInt(newYear,10);
    if (isNaN(newYear) || newYear<this.options.minDate.getFullYear() || newYear>this.options.maxDate.getFullYear()) {
      alert(RicoTranslate.getPhraseById("calInvalidYear"));
    } else {
      this.yearSelected=newYear;
      this.popDownYear();
      this.constructCalendar();
    }
  },
  
  incYear : function() {
    if (this.yearSelected>=this.options.maxDate.getFullYear()) return;
    this.yearSelected++;
    this.constructCalendar();
  },

  decYear : function() {
    if (this.yearSelected<=this.options.minDate.getFullYear()) return;
    this.yearSelected--;
    this.constructCalendar();
  },

  // tried a number of different week number functions posted on the net
  // this is the only one that produced consistent results when comparing week numbers for December and the following January
  WeekNbr : function(year,month,day) {
    var when = new Date(year,month,day);
    var newYear = new Date(year,0,1);
    var offset = 7 + 1 - newYear.getDay();
    if (offset == 8) offset = 1;
    var daynum = ((Date.UTC(year,when.getMonth(),when.getDate(),0,0,0) - Date.UTC(year,0,1,0,0,0)) /1000/60/60/24) + 1;
    var weeknum = Math.floor((daynum-offset+7)/7);
    if (weeknum == 0) {
      year--;
      var prevNewYear = new Date(year,0,1);
      var prevOffset = 7 + 1 - prevNewYear.getDay();
      weeknum = (prevOffset == 2 || prevOffset == 8) ? 53 : 52;
    }
    return weeknum;
  },

  constructCalendar : function() {
    var aNumDays = [31,0,31,30,31,30,31,31,30,31,30,31];
    var startDate = new Date (this.yearSelected,this.monthSelected,1);
    var endDate,numDaysInMonth,i,colnum;

    if (typeof this.monthSelected!='number' || this.monthSelected>=12 || this.monthSelected<0) {
      alert('ERROR in calendar: monthSelected='+this.monthSelected);
      return;
    }

    if (this.monthSelected==1) {
      endDate = new Date (this.yearSelected,this.monthSelected+1,1);
      endDate = new Date (endDate - (24*60*60*1000));
      numDaysInMonth = endDate.getDate();
    } else {
      numDaysInMonth = aNumDays[this.monthSelected];
    }
    var dayPointer = startDate.getDay() - this.options.startAt;
    if (dayPointer<0) dayPointer+=7;
    this.popDownMonth();
    this.popDownYear();

    this.bgcolor=Element.getStyle(this.tbody,'background-color');
    this.bgcolor=this.bgcolor.replace(/\"/g,'');
    if (this.options.showWeekNumber) {
      for (i=1; i<7; i++) {
        this.tbody.rows[i].cells[0].innerHTML='&nbsp;';
      }
    }
    for ( i=1; i<=dayPointer; i++ ) {
      this.resetCell(this.tbody.rows[1].cells[i]);
    }

    for ( var datePointer=1,r=1; datePointer<=numDaysInMonth; datePointer++,dayPointer++ ) {
      colnum=dayPointer % 7 + 1;
      if (this.options.showWeekNumber==1 && colnum==1) {
        this.tbody.rows[r].cells[0].innerHTML=this.WeekNbr(this.yearSelected,this.monthSelected,datePointer);
      }
      var dateClass=this.styles[colnum];
      if ((datePointer==this.dateNow)&&(this.monthSelected==this.monthNow)&&(this.yearSelected==this.yearNow)) {
        dateClass='ricoCalToday';
      }
      var c=this.tbody.rows[r].cells[colnum];
      c.innerHTML="&nbsp;" + datePointer + "&nbsp;";
      c.className=dateClass;
      var bordercolor=(datePointer==this.odateSelected) && (this.monthSelected==this.omonthSelected) && (this.yearSelected==this.oyearSelected) ? this.options.selectedDateBorder : this.bgcolor;
      c.style.border='1px solid '+bordercolor;
      var h=this.Holidays[this.holidayKey(this.yearSelected,this.monthSelected,datePointer)];
      if (!h)  {
        h=this.Holidays[this.holidayKey(0,this.monthSelected,datePointer)];
      }
      c.style.color=h ? h.txtColor : '';
      c.style.backgroundColor=h ? h.bgColor : '';
      c.title=h ? h.desc : '';
      if (colnum==7) r++;
    }
    while (dayPointer<42) {
      colnum=dayPointer % 7 + 1;
      this.resetCell(this.tbody.rows[r].cells[colnum]);
      dayPointer++;
      if (colnum==7) r++;
    }

    this.titleMonth.innerHTML = RicoTranslate.monthAbbr(this.monthSelected);
    this.titleYear.innerHTML = this.yearSelected;
    if (this.todayCell) {
      this.todayCell.innerHTML = RicoTranslate.getPhraseById("calToday",this.dateNow,RicoTranslate.monthAbbr(this.monthNow),this.yearNow,this.monthNow+1);
    }
  },
  
/** @private */
  resetCell: function(c) {
    c.innerHTML="&nbsp;";
    c.className='ricoCalEmpty';
    c.style.border='1px solid '+this.bgcolor;
    c.style.color='';
    c.style.backgroundColor='';
    c.title='';
  },
  
/** @private */
  saveAndClose : function(e) {
    Event.stop(e);
    var el=Event.element(e);
    var s=el.innerHTML.replace(/&nbsp;/g,'');
    if (s=='' || el.className=='ricoCalWeekNum') return;
    var day=parseInt(s,10);
    if (isNaN(day)) return;
    var d=new Date(this.yearSelected,this.monthSelected,day);
    var dateStr=d.formatDate(this.dateFmt=='ISO8601' ? 'yyyy-mm-dd' : this.dateFmt);
    if (this.returnValue) this.returnValue(dateStr);
    this.close();
  },

  open : function(curval) {
    if (!this.bPageLoaded) return;
    var today = new Date();
    this.dateNow  = today.getDate();
    this.monthNow = today.getMonth();
    this.yearNow  = today.getFullYear();
    if (typeof curval=='object') {
      this.dateSelected  = curval.getDate();
      this.monthSelected = curval.getMonth();
      this.yearSelected  = curval.getFullYear();
    } else if (this.dateFmt=='ISO8601') {
      var d=new Date();
      d.setISO8601(curval);
      this.dateSelected  = d.getDate();
      this.monthSelected = d.getMonth();
      this.yearSelected  = d.getFullYear();
    } else if (this.re.exec(curval)) {
      var aDate = [ RegExp.$1, RegExp.$3, RegExp.$5 ];
      this.dateSelected  = parseInt(aDate[this.dateParts.dd], 10);
      this.monthSelected = parseInt(aDate[this.dateParts.mm], 10) - 1;
      this.yearSelected  = parseInt(aDate[this.dateParts.yyyy], 10);
      if (this.yearSelected < 100) {
        // apply a century to 2-digit years
        this.yearSelected+=this.yearNow - (this.yearNow % 100);
        var maxyr=this.options.maxDate.getFullYear();
        while (this.yearSelected > maxyr) this.yearSelected-=100;
      }
    } else {
      if (curval) {
        alert('ERROR: invalid date passed to calendar ('+curval+')');
      }
      this.dateSelected  = this.dateNow;
      this.monthSelected = this.monthNow;
      this.yearSelected  = this.yearNow;
    }
    this.odateSelected=this.dateSelected;
    this.omonthSelected=this.monthSelected;
    this.oyearSelected=this.yearSelected;
    this.constructCalendar();
    this.openPopup();
  }
});

Rico.includeLoaded('ricoCalendar.js');
