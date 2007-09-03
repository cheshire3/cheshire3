
from parser import XmlRecordStoreParser
import bsddb as bdb
import os

class CNWStoreParser(XmlRecordStoreParser):
    idNormaliser = None
    cxn = None

    def __init__(self, parent, config):
        self.cxn = None
        XmlRecordStoreParser.__init__(self, parent, config)
        dbp = self.get_path(None, "databasePath")
        if (not os.path.isabs(dbp)):
            # Prepend defaultPath from parents
            dfp = self.get_path(None, 'defaultPath')
            if (not dfp):
                raise(ConfigFileException("RecordStore has relative path, and no visible defaultPath."))
            dbp = os.path.join(dfp, dbp)
        self.paths['databasePath'] = dbp
        self.idNormaliser = self.get_path(None, 'idNormaliser')
        self._verifyDatabase()


    def _verifyDatabase(self):
        dbp = self.get_path(None, 'databasePath')
        if (not os.path.exists(dbp)):
            # We don't exist, try and instantiate new database
            self._initialise()
        else:
            cxn = bdb.db.DB()
            try:
                cxn.open(dbp)
                cxn.close()
            except:
                # Still don't exist
                self._initialise()

    def _initialise(self):
        cxn = bdb.db.DB()
        cxn.open(self.get_path(None, 'databasePath'), dbtype=bdb.db.DB_BTREE, flags = bdb.db.DB_CREATE, mode=0660)
        holdings = self.get_path(None, 'holdingsPath')
        if (not os.path.exists(holdings)):
            raise FileDoesNotExistException()
        else:
            f = file(holdings)
            lns = f.readlines()
            f.close()
            for l in lns:
                # cardid normal # comments
                if (l[0] <> "#"):
                    stuff = l.split()
                    sid = stuff[0]
                    if (len(stuff) > 1):
                        nml = stuff[1]
                    else:
                        nml = '0'
                    if (self.idNormaliser):
                        sid = self.idNormaliser.process_string(session, sid)
                    cxn.put(sid, "%s" % (nml))
        cxn.close()

    def _openContainer(self):
        if self.cxn == None:
            cxn = bdb.db.DB()
            cxn.open(self.get_path(None, 'databasePath'), flags=bdb.db.DB_NOMMAP)
            self.cxn = cxn

    def _closeContainer(self):
        if self.cxn <> None:
            self.cxn.sync()
            self.cxn.close()
            self.cxn = None
       
    def process_document(self, session, doc):
        rec = XmlRecordStoreParser.process_document(self, session, doc)
        # Now get price etc info
        sid = str(rec.id)
        if (self.idNormaliser):
            sid = self.idNormaliser.process_string(session, sid)
        self._openContainer()
        val = self.cxn.get(sid)
        rec.holdings = 0
        self._closeContainer()
        if (val):
            rec.holdings = int(val)
        return rec

    def dump_holdings(self, session):
        # Write holdings text dump
	recStore = self.parent.get_object(session, 'l5rRecordStore')
	totalRecords = self.parent.totalRecords
	holdings = self.get_path(None, 'holdingsPath')
        if (os.path.exists(holdings)):
            os.rename(holdings, holdings + "_OLD")
        self._openContainer()
        o = file(holdings, 'w')
	for cardid in range(totalRecords):
	    self._openContainer()
	    nml = self.cxn.get(str(cardid))
	    if not nml:
		nml = 0
	    rec = recStore.fetch_record(session, int(cardid))	    
	    title = rec.process_xpath("name")
	    title = title[0][1][2:]
	    o.write('%s %s # %s\n' % (cardid, nml, title))
	o.flush()
	o.close()
	self._closeContainer()

    def batch_update_holdings(self, session, holdings):
        f = file(holdings)
        lns = f.readlines()
        f.close()
        for l in lns:
            # cardid normal # comments
            if (l[0] <> "#"):
                stuff = l.split()
                sid = stuff[0]
                if (len(stuff) > 1):
                    nml = int(stuff[1])
                    if (nml):
                        self.update_holdings(session, sid, nml)
                        print sid
               
    def update_holdings(self, session, card, normal):
        self._closeContainer()
        self._openContainer()
        sid = str(card)
        if (self.idNormaliser):
            sid = self.idNormaliser.process_string(session, sid)
        val = self.cxn.get(sid)
        if (val):
            n = int(val)
        else:
            n = 0
        nml =  n + normal
        self.cxn.put(sid, "%s" % (max(0,nml)))
        self._closeContainer()
        return nml
