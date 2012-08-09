# -*- coding: iso-8859-1 -*-

import os

from cheshire3.documentFactory import AccumulatingStream
from cheshire3.documentFactory import AccTransformerStream
from cheshire3.documentFactory import AccumulatingDocumentFactory
from cheshire3.documentFactory import SimpleDocumentFactory
from cheshire3.document import StringDocument
from cheshire3.formats.reportLab import NumberedCanvas


#get report lab stuff
from reportlab import platypus
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import NextPageTemplate
from reportlab.pdfgen import canvas

import reportlab.rl_config
reportlab.rl_config.warnOnMissingFontGlyphs = 0
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont



styles = getSampleStyleSheet()
HeaderStyle = styles["Heading1"]
ParagraphStyle = styles["Normal"]
ParagraphStyle.spaceBefore = 10
ParagraphStyle.spaceAfter = 10
ParagraphStyle.fontSize = 10




class ReportLabAccumulatingStream(AccumulatingStream):
    
    def __init__(self, session, stream, format, tagName=None, codec=None, factory=None ):
              
        self.data = []
        AccumulatingStream.__init__(self, session, stream, format, tagName, codec, factory)

    def accumulate(self, session, stream, format, tagName=None, codec=None, factory=None ):
        doc = StringDocument(stream.get_xml(session))#get rec into doc
        self.data.append(doc.get_raw(session))
        
        
    def find_documents(self, session, cache=0):
        yield self.data



class ReportLabAccTransformerStream(AccTransformerStream):
    
    def find_documents(self, session, cache=0):
        yield self.data



class ReportLabDocumentFactory(AccumulatingDocumentFactory):
    
    
    _possibleSettings = {'header' : {'docs' : "The string of text to be used as the header"},
                         'footer' : {'docs' : "The string of text to be used as the footer use [date] to add the date and [pages] to add page numbers"},
                         'psfont' : {'docs' : "String for Post script font to use can be helvetica, courier or times-roman only"},
                         'ttfontNormal' : {'docs' : ""},
                         'ttfontBold' : {'docs' : ""},
                         'ttfontItalic' : {'docs' : ""},
                         'ttfontBoldItalic' : {'docs' : ""},
                         'columns' : {'docs' : "Should the output have two columns on the page or just use the full page width (1 = columns, 0 = fullPage)"}
                         }


    def __init__(self, session, config, parent):
        AccumulatingDocumentFactory.__init__(self, session, config, parent)
        # text to use as header and footer plus switch for columns or not
        self.headerString = self.get_setting(session, 'header', None)
        self.footerString = self.get_setting(session, 'footer', None)
        self.columns = int(self.get_setting(session, 'columns', 0))
        
        #font crap       
        #psfont can either be helvetica (default), courier or times-roman
        #TTfonts need to be installed on the system and all 4 font types need to be specified with a path to their installed location (needed for some obscure accented characters outside - Latin 1 and 2 I think)
        self.psfont = self.get_setting(session, 'psfont', 'helvetica')
        self.ttfontNormal = self.get_setting(session, 'ttfontNormal', None)        
        self.ttfontBold = self.get_setting(session, 'ttfontBold', None)        
        self.ttfontItalic = self.get_setting(session, 'ttfontItalic', None)        
        self.ttfontBoldItalic = self.get_setting(session, 'ttfontBoldItalic', None)
        if self.ttfontNormal is not None:
            self.normaltag = self.ttfontNormal[self.ttfontNormal.rfind('/')+1:self.ttfontNormal.rfind('.')]
            self.boldtag = self.ttfontBold[self.ttfontBold.rfind('/')+1:self.ttfontBold.rfind('.')]
            self.italictag = self.ttfontItalic[self.ttfontItalic.rfind('/')+1:self.ttfontItalic.rfind('.')]
            self.bolditalictag = self.ttfontBoldItalic[self.ttfontBoldItalic.rfind('/')+1:self.ttfontBoldItalic.rfind('.')]
             
            pdfmetrics.registerFont(TTFont(self.normaltag, self.ttfontNormal))
            pdfmetrics.registerFont(TTFont(self.boldtag, self.ttfontBold))
            pdfmetrics.registerFont(TTFont(self.italictag, self.ttfontItalic))
            pdfmetrics.registerFont(TTFont(self.bolditalictag, self.ttfontBoldItalic))               
            registerFontFamily(self.normaltag,normal=self.normaltag,bold=self.boldtag,italic=self.italictag,boldItalic=self.bolditalictag)
            ParagraphStyle.fontName = self.normaltag
        else:
            ParagraphStyle.fontName = self.psfont
           
    def get_document(self, session, n=-1):
        if self.previousIdx == -1:
            self.generator = self.prepareReport(session)
            
        return SimpleDocumentFactory.get_document(self, session, n)
    
    
    def getData(self, session):
        paras = []
        gen = self.docStream.find_documents(session, cache=self.cache)
        for text in gen:     
            for t in text:
                paras.append(platypus.Paragraph(t, ParagraphStyle, bulletText=None))
                paras.append(NextPageTemplate("noHeader"))
        return paras  
    
    def prepareReport(self, session):
        #this is the report lab set up stuff
        OutputElements=[]
        
        output = platypus.BaseDocTemplate('/tmp/temp.pdf')
        
        #A4 page size setup with margins
        output.pagesize = (8.3*inch, 11.7*inch)
        output.leftMargin = 0.5*inch
        output.rightMargin = 0.5*inch
        output.topMargin = 0.5*inch
        output.bottomMargin = 0.5*inch
        output.width = output.pagesize[0] - output.leftMargin - output.rightMargin
        output.height = output.pagesize[1] - output.topMargin - output.bottomMargin
        
        
        if self.columns == 1:
            #set up the columns
            interFrameMargin = 0.5*inch
            frameWidth = output.width/2 - interFrameMargin/2
            frameHeight = output.height - inch*0.6
            framePadding = 0*inch
        
            # create a frameset called withHeader
            withHeader = []
            # append header settings and 2 columns
            leftMargin = output.leftMargin
            titlebar = platypus.Frame(leftMargin, output.height, output.width, 0.75*inch, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, showBoundary=0)
            withHeader.append(titlebar)
            
            column = platypus.Frame(leftMargin, output.bottomMargin, frameWidth, frameHeight)
            withHeader.append(column)
        
            leftMargin = output.leftMargin + frameWidth + interFrameMargin
            column = platypus.Frame(leftMargin, output.bottomMargin, frameWidth, frameHeight)
            withHeader.append(column)
           
            #create frameset called withoutHeader
            withoutHeader = []
            
            #change the frame height because no header here
            frameHeight = output.height - inch*0.2
            #add two columns
            leftMargin = output.leftMargin
            column = platypus.Frame(leftMargin, output.bottomMargin, frameWidth, frameHeight)
            withoutHeader.append(column)
        
            leftMargin = output.leftMargin + frameWidth + interFrameMargin
            column = platypus.Frame(leftMargin, output.bottomMargin, frameWidth, frameHeight)
            withoutHeader.append(column)
        else:
            #set up the full page stuff
            frameWidth = output.width
            frameHeight = output.height - inch*0.6
            framePadding = 0*inch
            
            withHeader = []
            
            #append header and single column (full page)
            leftMargin = output.leftMargin
            titlebar = platypus.Frame(leftMargin, output.height, output.width, 0.75*inch, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, showBoundary=0)
            withHeader.append(titlebar)
            
            column = platypus.Frame(leftMargin, output.bottomMargin, frameWidth, frameHeight)
            withHeader.append(column)            
            
            withoutHeader = []
            
            frameHeight = output.height - inch*0.2
            column = platypus.Frame(leftMargin, output.bottomMargin, frameWidth, frameHeight)
            withoutHeader.append(column)            
            
        
        def header(Elements, txt, style=HeaderStyle):
            s = platypus.Spacer(0.2*inch, 0.2*inch)
            Elements.append(s)
            style.alignment=1
            style.fontName=self.psfont
            style.fontSize=18
            style.borderWidth=0
            para = platypus.Paragraph(txt, style)
            Elements.append(para)  
    
        headerPage = platypus.PageTemplate(id='Header',frames=withHeader)
        normalPage = platypus.PageTemplate(id='noHeader',frames=withoutHeader)
        
        if self.headerString is not None:
            output.addPageTemplates([headerPage, normalPage])
            header(OutputElements, self.headerString)
            OutputElements.append(platypus.FrameBreak())
        else:
            output.addPageTemplates([normalPage])
            
        OutputElements.extend(self.getData(session))
        
        #numbered canvas does footer (including page numbers and date is requested)
        NumberedCanvas.setFooterText(self.footerString)
        output.build(OutputElements, canvasmaker=NumberedCanvas)
        output.showBoundary = True
        fileInput = open('/tmp/temp.pdf', 'r')
        doc = StringDocument(fileInput.read())
        os.remove('/tmp/temp.pdf')
        yield doc
    
ReportLabDocumentFactory.register_stream('reportlabTxr', ReportLabAccTransformerStream)    
ReportLabDocumentFactory.register_stream('reportlab', ReportLabAccumulatingStream)
    