import requests, asyncio, websockets,json,os, glob,sys,random,time,logging
from datetime import datetime
from pathlib import Path
from aioconsole import ainput
sys.path.append('..')
from website_base import *


DEBUG = False
token_url = "https://api.play-gaming.com/auth/v2/GetTokenBySiteId/85"
websocket_url = "wss://sbapi.sbtech.com/betpt/sportscontent/sportsbook/v1/Websocket?jwt=token&locale=pt"

#replace $SPORT_ID$ by the specified sports and $DATE$
rpc_sport_message = '''{"jsonrpc":"2.0","params":{"eventState":"Mixed","eventTypes":["Fixture"],"ids":[$SPORT_ID$],"dateRange":{"from":$DATE$,"timeRange":"OneDay"},"pagination":{"top":300,"skip":0},"eventTags":[],"marketTypeRequests":[{"sportIds":[$SPORT_ID$],"marketTypeIds":["1_39","3_249","158","1_0","3_200"],"statement":"Include"}],"excludeRegionIds":["180"],"leagueState":"Regular"},"method":"GetEventsBySportId","meta":{"blockId":"html-container-Center_TodaysEventsResponsiveBlock_31094"},"id":"73e9c73d-99bf-4332-9a9f-fed0a9f0ead5"}'''


MARKET_TYPE_OVERALL_WIN = "1_0"

json_unsub_rpc_message = {
    "jsonrpc":"2.0",
    "params":{},
    "method":"Unsubscribe",
    "meta":{},
    "id":"66f71ee3-7663-4c35-8938-8cebb92ff0f3"
}

json_query_rpc_message = {
    "jsonrpc" : "2.0",
    "params": {
        "eventState":"Mixed",
        "eventTypes":["Fixture"],
        "ids":["$SPORT_ID$"],
        "dateRange":{"from":"$DATE$","timeRange":"OneDay"},
        "pagination":{"top":300,"skip":0},
        "eventTags":[],
        "marketTypeRequests":[
            {"sportIds":["$SPORT_ID$"],
                "marketTypeIds":["1_39","3_249","158",MARKET_TYPE_OVERALL_WIN,"3_200"],
                "statement":"Include"
            }
        ],
        "excludeRegionIds":["180"],
        "leagueState":"Regular"
    },
    "method":"GetEventsBySportId",
    "meta":{"blockId":"html-container-Center_TodaysEventsResponsiveBlock_31094"},
    "id":"73e9c73d-99bf-4332-9a9f-fed0a9f0ead5"
}

def getRpcQueryMessage(sports,date,id):
    json_query_rpc_message['params']['ids'] = sports
    json_query_rpc_message['params']['marketTypeRequests'][0]["sportIds"] = sports
    json_query_rpc_message['params']['dateRange']["from"] = date
    json_query_rpc_message['id'] = str(id)
    return json.dumps(json_query_rpc_message,default=str)

def getRpcUnsubscribeMessage(id):
    json_unsub_rpc_message['id'] = str(id)
    return json.dumps(json_unsub_rpc_message,default=str)


SPORT_IDS = {
    1:FUTEBOL_MATCH_TYPE,
    6:TENIS_MATCH_TYPE,
    2:BASTQUETEBOL_MATCH_TYPE,
    8:HOQUEI_GELO_MATCH_TYPE,
    10:ANDEBOL_MATCH_TYPE,
    7:BASEBOL_MATCH_TYPE,
    25:FUTSAL_MATCH_TYPE,
}




def debug_print(*args,**kwargs):
    result_str = ""
    for arg in args:
        result_str+=str(arg)
    logging.debug(result_str,**kwargs)



class BetPt(WebsiteBase):

    def __init__(self,**kwargs):
        WebsiteBase.__init__(self,"BetPT",**kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.setupWebsocket())
        self.rawData = loop.run_until_complete(self.queryData())


    async def setupWebsocket(self):
        token = self.get_auth_token()
        self.websocket = await websockets.connect(websocket_url.replace("token",token),max_size=2**26)#read_limit=2 ** 25)

    
    #Should return an object that will be used on parsing
    def getMatch(self,event_id):
        results = []
        for each in self.rawData['result']['markets']:
            if event_id == each['eventId']:
                results.append(each)
        if len(results) == 0:
            raise Exception("Error getting match bet")
        return results

    #Parsing functions, all should return BetType
    def parseFRBet(self,match):
        for market in match:
            if market['marketType']["id"] == MARKET_TYPE_OVERALL_WIN:
                selection_list = [None,None,None]
                name_market = market['name']
                for selection in market['selections']:
                    name_bet = selection['name']
                    event_id = market['eventId']

                    if(selection['points'] != None):
                        name_bet += " " + str(selection['points'])

                    odds = str(selection['trueOdds'])
                    if selection['outcomeType'] == "Home":
                        selection_list[0] = {'odd':odds,'name':name_bet}
                    elif selection['outcomeType'] == "Away":
                        selection_list[2] = {'odd':odds,'name':name_bet}
                    elif selection['outcomeType'] == "Tie":
                        selection_list[1] = {'odd':odds,'name':name_bet}
                
                try:
                    while True:
                        selection_list.remove(None)
                except ValueError:
                    pass

                return BetType(selection_list,event_id,name_market)
        raise Exception("Error parsing FR Bet")

    #Should return a list of GameMatch
    def getMatchList(self):
        temp_set = set()
        result = []
        for each in self.rawData['result']['events']:
            if each['id'] not in temp_set:
                temp_set.add(each['id'])
                betRadarID = 0
                if len(each['media']) > 0:
                    for media in each['media']:
                        if media['providerName'] == "BetRadar":
                            betRadarID = media['providerEventId']

                if betRadarID == 0:
                    if self.debug:
                        print("Error getting betRadarInfo for match",each['betslipLine'])
                        dumpJsonFile(self.websiteName+"_"+str(each['id'])+".json",each)
                    continue
                result.append(GameMatch(each['id'],SPORT_IDS[each['sportOrder']],each['betslipLine'],betRadarID))
        
        return result

    def saveRawEvent(self,match_id,filename):
        dumpJsonFile(filename,self.getMatch(match_id))
    
    def saveRawMatchList(self,filename):
        dumpJsonFile(filename,self.rawData['result']['events'])


    async def queryData(self):
        id = str(random.randint(1,99999999999))
        query = getRpcQueryMessage([str(sport) for sport in SPORT_IDS.keys()],time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),id)
        unsub_msg = getRpcUnsubscribeMessage(id)
        debug_print("----NEW_MESSAGE_SENT----")
        debug_print(query)
        debug_print("------------------------")
        await self.websocket.send(query)
        await self.websocket.send(unsub_msg)
        return await self.recvMessage(id)

    def get_auth_token(self):
        val = requests.get(url=token_url)
        if val.ok:
            debug_print("Auth token response=",val.text)
        else:
            raise Exception('Error requesting auth token')
        return val.json()['token']

    async def recvMessage(self,id):
        while True:
            try:
                message = await asyncio.wait_for(self.websocket.recv(),10)
                json_obj = json.loads(message)
                debug_print("----NEW_MESSAGE_RECIEVED----")
                debug_print(json_obj)
                debug_print("Length:",len(message))
                debug_print("----------------------------")
                if "error" in json_obj:
                    print("Server returned error message:",json_obj['error']['message'])
                    print(json_obj)
                #dumpJsonFile("file"+str(i)+".json",json_obj)
                if json_obj['id'] == id:
                    return json_obj
            except asyncio.TimeoutError:
                debug_print('Timeout has been reached for a recived message')

    
    #loop.run_forever() 