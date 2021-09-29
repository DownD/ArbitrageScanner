import requests, asyncio, websockets,json,os, glob,sys,random,time,logging
from datetime import datetime
from pathlib import Path
sys.path.append('..')
from website_base import *


SPORT_IDS = {
    1:FUTEBOL_MATCH_TYPE,
    6:TENIS_MATCH_TYPE,
    2:BASTQUETEBOL_MATCH_TYPE,
    8:HOQUEI_GELO_MATCH_TYPE,
    10:ANDEBOL_MATCH_TYPE,
    7:BASEBOL_MATCH_TYPE,
    25:FUTSAL_MATCH_TYPE,
}

MARKET_TYPE_OVERALL_WIN = "1_0"


#Replace $SPORT$
MATCH_LIST_URL = "https://sbapi.sbtech.com/betwaypt/sportsdata/v2/events?query=$filter=sportId%20eq%20'$SPORT$'&includeMarkets=none&timeRange=OneDay"

#Replace $EVENT_ID$
MATCH_URL = "https://sbapi.sbtech.com/betwaypt/sportsdata/v2/markets?query=$filter=eventId%20eq%20'$EVENT_ID$'"

#Auth endpoint
AUTH_URL = "https://api.play-gaming.com/auth/v2/GetTokenBySiteId/194"

#{"jsonrpc":"2.0","params":{"eventState":"Mixed","eventTypes":["Fixture","AggregateFixture"],"ids":["44069"],"regionIds":["180"],"pagination":{"top":100,"skip":0},"marketTypeRequests":[{"sportIds":["1"],"marketTypeIds":["1_39","2_39","3_39","1_169","1707","1_0","2_0","3_0"],"statement":"Include"}]},"method":"GetEventsByLeagueId","meta":{"blockId":"eventsWrapper-Center_LeagueViewResponsiveBlock_15984"},"id":"fa52f8c2-d8e2-450c-ab78-866ecfd03044"}
#{"jsonrpc":"2.0","params":{"eventState":"Mixed","eventTypes":["Outright"],"pagination":{"top":100,"skip":0},"ids":["44069"]},"method":"GetEventsByLeagueId","meta":{"blockId":"outRights-html-container-Center_LeagueViewResponsiveBlock_15984Center_LeagueViewResponsiveBlock_15984"},"id":"70406497-4ee6-471b-9a4d-d428816cc3d9"}
class Betway(WebsiteBase):
    def __init__(self,**kwargs):
        WebsiteBase.__init__(self,"Betaway",**kwargs)

        token_answer = requests.get(url=AUTH_URL)
        if token_answer.ok:
            self.bearer_token = token_answer.json()['token']
        else:
            raise Exception("Error getting auth Betaway auth token message="+str(token_answer.text))


    #Parsing functions, all should return BetType, allways take the result returned by getMatch
    #The order has to be home_win, tie, away_win
    def parseFRBet(self,match):
        for market in match['data']:
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
        raise Exception("Error parsing FR bet, no final result found")


    #Should return a list of GameMatches
    def getMatchList(self):
        result = [] 
        for sport in SPORT_IDS:
            data_json = self.doGetJsonRequest(url=MATCH_LIST_URL.replace("$SPORT$",str(sport))) 
            for each in data_json['data']['events']:
                betRadarID = 0
                if len(each['media']) > 0:
                    for media in each['media']:
                        if "BetRadar" in media['providerName']:
                            betRadarID = media['providerEventId']

                if betRadarID == 0:
                    logging.warning("Error getting Betaway betRadarInfo for match " +str(each['betslipLine'] + " with id "+ str(each['id'])))
                    if self.debug:
                        dumpJsonFile(self.websiteName+"_"+str(each['id'])+".json",each)
                    continue
                result.append(GameMatch(each['id'],SPORT_IDS[sport],each['betslipLine'],betRadarID))
        
        return result


    #Should return an object that will be used on parsing
    #In order to debug, should be in json format
    def getMatch(self,id):
        return self.doGetJsonRequest(url=MATCH_URL.replace("$EVENT_ID$",str(id)))

    #Saves the raw event file
    def saveRawEvent(self,match_id,filename):
        match = self.getMatch(match_id)
        if match != None:
            dumpJsonFile(filename,self.getMatch(match_id))

    #Saves the raw match list file
    def saveRawMatchList(self,filename):
        result = [] 
        for sport in SPORT_IDS:
            data_json = self.doGetJsonRequest(url=MATCH_LIST_URL.replace("$SPORT$",str(sport))) 
            result.append({sport:data_json})
            dumpJsonFile(filename,result)

    def doGetJsonRequest(self,*args,**kwargs):
        if 'headers' in kwargs:
            kwargs['headers']['Authorization'] = 'Bearer ' + str(self.bearer_token)
        else:
            kwargs['headers'] = {"Authorization": "Bearer " + str(self.bearer_token)}

        val = requests.get(*args,**kwargs)
        if not val.ok:
            raise Exception("Error on request " +str(val.text))
        
        return val.json()



if __name__ == '__main__':
    betaway = Betway(debug=True)
    betaway.saveRawMatchList("btaway_match_list.json")
    #exit()
    matches = betaway.getMatchList()
    print("Found",len(matches))
    for match in matches:
        try:
            betaway.parseFRBet(betaway.getMatch(match.id)) 
        except Exception as e:
            print(e)
            
    #for match in matches:
        #dumpJsonFile("betano_match_"+str(match.id)+".json",betano.getMatch(match.id))