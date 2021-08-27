import time

from core.models import action

from core import db, helpers, logging
from core import model, cache

from plugins.asset.models import asset

class _assetRelationship(db._document):
    timespan = int()
    data = dict()
    fromAsset = str()
    toAsset = str()

    _dbCollection = db.db["assetRelationship"]

    # def addRelationship(self, acl, timespan, fromAsset, toAsset, data, count):
    #     try:
    #         result = cache.globalCache.get("dbModelCache",self.__class__.__name__,getClassByName,extendCacheTime=True)[0]
    #         self._dbCollection.update_one({ "timespan" : timespan, "fromAsset" : fromAsset, "toAsset" : toAsset, "data" : data, "classID" : result["_id"] },{ "$set" : { "acl" : acl, "lastSeen" : int(time.time()) }, "$inc" : { "count" : count } },upsert=True)
    #     except:
    #         pass

    def bulkNew(self, acl, timespan, fromAsset, toAsset, data, bulkClass):
        self.acl = acl
        self.timespan = timespan
        self.fromAsset = fromAsset
        self.toAsset = toAsset
        self.data = data
        return super(_assetRelationship, self).bulkNew(bulkClass)

class _assetRelationshipUpdate(action._action):
    relationshipData = dict()
    fromAsset = str()
    toAsset = str()
    timespan = int()

    def __init__(self):
        self.bulkClass = db._bulk()
        cache.globalCache.newCache("assetRelationshipCache")

    def postRun(self):
        self.bulkClass.bulkOperatonProcessing()

    def run(self,data,persistentData,actionResult):
        relationshipData = helpers.evalDict(self.relationshipData,{"data" : data})
        fromAsset = helpers.evalString(self.fromAsset,{"data" : data})
        toAsset = helpers.evalString(self.toAsset,{"data" : data})

        timespan = 3600
        if self.timespan > 0:
            timespan = self.timespan
        timespan = helpers.roundTime(roundTo=timespan).timestamp()

        match = "{0}={1}->{2}".format(timespan,fromAsset,toAsset)
        # This will cause a memory leak overtime as globalCache is not cleared down --- this needs to be fixed
        relationship = cache.globalCache.get("assetRelationshipCache",match,getAssetRelationshipObject,timespan,fromAsset,toAsset,extendCacheTime=True)
        if not relationship:
            relationshipItem = _assetRelationship().bulkNew(self.acl,timespan,fromAsset,toAsset,relationshipData,self.bulkClass)
            if relationshipItem:
                cache.globalCache.insert("assetRelationshipCache",match,[relationshipItem])

        actionResult["result"] = True
        actionResult["rc"] = 0
        return actionResult

class _assetRelationshipBulkUpdate(action._action):
    relationshipData = dict()
    fromAssetField = str()
    toAssetField = str()
    timespan = int()
    eventField = str()

    def __init__(self):
        self.bulkClass = db._bulk()
        cache.globalCache.newCache("assetRelationshipCache")

    def postRun(self):
        self.bulkClass.bulkOperatonProcessing()

    def run(self,data,persistentData,actionResult):
        relationshipData = helpers.evalDict(self.relationshipData,{"data" : data})
        events = helpers.evalString(self.eventField,{"data" : data})

        timespan = 3600
        if self.timespan > 0:
            timespan = self.timespan
        timespan = helpers.roundTime(roundTo=timespan).timestamp()

        matches={}
        for event in events:
            matches["{0}->{1}".format(event[self.fromAssetField],event[self.toAssetField])] = event
        
        results = _assetRelationship().query(query={"timespan" : timespan },fields=["fromAsset","toAsset"])["results"]
        for result in results:
            match = "{0}->{1}".format(result["fromAsset"],result["toAsset"])
            if match in matches:
                del matches[match]

        for match in matches:
            _assetRelationship().bulkNew(self.acl,timespan,matches[match][self.fromAssetField],matches[match][self.toAssetField],relationshipData,self.bulkClass)

        actionResult["result"] = True
        actionResult["rc"] = 0
        return actionResult

def getClassByName(match,sessionData):
    return model._model(False).query(query={"className" : match})["results"]

def getAssetRelationshipObject(match,sessionData,timespan,fromAsset,toAsset):
    try:
        _assetRelationship().query(query={ "timespan" : timespan, "fromAsset" : fromAsset, "toAsset" : toAsset },limit=1)["results"][0]
        return True
    except:
        return None