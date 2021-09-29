import json,requests,os,logging
from os import name
from pathlib import Path
import sys
sys.path.append('..')
from website_base import *

SPORT_IDS = {
    1:FUTEBOL_MATCH_TYPE,
    2:TENIS_MATCH_TYPE,
    3:F1_MATCH_TYPE,
    4:BASTQUETEBOL_MATCH_TYPE,
    5:RUGBY_MATCH_TYPE,
    8:VOLEIBOL_MATCH_TYPE,
    9:ANDEBOL_MATCH_TYPE,
    13:HOQUEI_GELO_MATCH_TYPE,
    14:FOTEBOL_AMERICANO_MATCH_TYPE,
    15:MOTOCICLISMO_MATCH_TYPE, 
    20:BASEBOL_MATCH_TYPE,
    24:NASCAR_MATCH_TYPE,
    52:RUGBY_MATCH_TYPE
}


#Replace $SPORTID$ and $LIMIT$
LIST_SPORT_ENDPOINT = "https://offer.cdn.begmedia.com/api/pub/v4/events?application=1024&countrycode=pt&fetchMultipleDefaultMarkets=true&language=pt&limit=$LIMIT$&offset=0&sitecode=ptpt&sortBy=ByLiveRankingPreliveDate&sportIds=$SPORTID$"

#Replace $EVENTID$
SPORT_ENDPOINT = "https://offer.cdn.begmedia.com/api/pub/v4/events/$EVENTID$?application=1024&countrycode=pt&language=pt&sitecode=ptpt"


class BetClic(WebsiteBase):
    def __init__(self,**kwargs):
        WebsiteBase.__init__(self,"BetClic",**kwargs)
        self.MATCH_ODDS = {
                #id:{name:_name,sport_name:_sport_name,betRadarID:_id}
        }
        self.insertData()

        

    #Should return a list of GameMatch
    def getMatchList(self):
        return [GameMatch(id,m['sport_name'],m['name'],m['betRadarID']) for id,m in self.MATCH_ODDS.items()]


    #Should return an object that will be used on parsing
    def getMatch(self,event_id):
        return self.getEvent(event_id)

    #Parsing functions, all should return BetType
    def parseFRBet(self,match):
        for market in match['markets']:
            market_name = market['name']
            
            if market['mtc'] == 'Bsb_Mwi' or market['mtc'] == 'Ftb_Mr3' or market['mtc'] == 'Ten_Mr2' or market['mtc'] == 'Ihk_Mrs' or market['mtc'] == 'Bkb_Mr6' or market['mtc'] == 'Hdb_Mr2' or market['mtc'] == 'Vlb_Mr2':
            #if market_name == "Resultado (Tempo Regulamentar)":
                selections = []
                for bet in market['selections']:
                    bet_name = bet['name']
                    bet_odd = bet['odds']
                    selections.append({"name":bet_name,"odd":bet_odd})
                return BetType(selections,match["match_id"],market['name'])
        
        raise Exception("Error parsing FR Bet")
        
    def saveRawEvent(self,match_id,filename):
        dumpJsonFile(filename,self.getEvent(match_id))

    def saveRawMatchList(self,filename):
        dumpJsonFile(filename,self.getSportsList())

    def getEvent(self,eventID):
        val = requests.get(url=SPORT_ENDPOINT.replace("$EVENTID$",str(eventID)))
        if not val.ok:
            raise Exception("Error grabbing sport event id:"+str(eventID))

        result = val.json()
        result['match_id'] = eventID
        return result

    def getSportsList(self,sport=None):
        sport_ids = []
        if sport == None:
            sport_ids = SPORT_IDS.keys()
        else:
            sport_ids.append(sport)

        result_list = {}

        for each in sport_ids:
            val = requests.get(url=LIST_SPORT_ENDPOINT.replace("$SPORTID$",str(each)).replace('$LIMIT$',"500"))
            if not val.ok:
                raise Exception("Error grabbing sport list id:"+str(sport))

            result_list[SPORT_IDS[each]] = val.json()

        return result_list

    def insertData(self):
        sports = self.getSportsList()
        for id_sport,dic_matches in sports.items():
            for match in dic_matches:
                if("betRadarInfo" in match):
                    self.MATCH_ODDS[match['id']] = {"name":match['name'],"sport_name":id_sport,"betRadarID":match['betRadarInfo']['id']}
                else:
                    logging.warning("Error parsing betRadarInfo for match " + str(match['name']) +" on Betclic")
                    if self.debug:
                        dumpJsonFile(self.websiteName+"_"+str(match['id'])+".json",match)
    
if __name__ == '__main__':
    betclic = BetClic()
    betclic.saveRawMatchList("matches.json")