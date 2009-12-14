# -*- coding: iso-8859-1 -*-
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

import datetime

#this sets up a canvas with footnote, page numbers and date if requested in the cheshire3 config
class NumberedCanvas(canvas.Canvas):
    
    footer = ""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)     
        self._codes = []

     
    @classmethod
    def setFooterText(cls, text):
        global footer
        text = text.replace('[date]', str(datetime.date.today()))
        footer = text
        
        
    def showPage(self):
        self._codes.append({'code': self._code, 'stack': self._codeStack})
        self._startPage()
        
        
    def save(self):
        global footer

        # reset page counter 
        self._pageNumber = 0
        for code in self._codes:
            # recall saved page
            self._code = code['code']
            self._codeStack = code['stack']
            self.setFont("Helvetica", 7)
            self.drawRightString(200*mm, 10*mm, footer.replace('[pages]', 'page %i of %i' % (self._pageNumber+1, len(self._codes))), )
            canvas.Canvas.showPage(self)
        self._doc.SaveToFile(self._filename, self)