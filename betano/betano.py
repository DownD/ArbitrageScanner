import requests, asyncio, websockets,json,os, glob,sys,random,time
from datetime import datetime
from pathlib import Path
sys.path.append('..')
from website_base import *


SPORT_IDS = {
    "futebol/jogos-de-hoje":FUTEBOL_MATCH_TYPE,
    "tenis/jogos-de-hoje":TENIS_MATCH_TYPE,
    #"formula-1":F1_MATCH_TYPE,
    "basquetebol/jogos-de-hoje":BASTQUETEBOL_MATCH_TYPE,
    #"rugby-league":RUGBY_MATCH_TYPE,
    #"rugby-union":RUGBY_MATCH_TYPE,
    "voleibol/jogos-de-hoje":VOLEIBOL_MATCH_TYPE,
    "andebol/jogos-de-hoje":ANDEBOL_MATCH_TYPE,
    "hoquei-no-gelo/jogos-de-hoje":HOQUEI_GELO_MATCH_TYPE,
    #"futebol-americano/jogos-de-hoje":FOTEBOL_AMERICANO_MATCH_TYPE,
    #"motogp":MOTOCICLISMO_MATCH_TYPE, 
    "basebol/jogos-de-hoje":BASEBOL_MATCH_TYPE,
}



#Replace $SPORT$
MATCH_LIST_URL = "https://www.betano.pt/api/sport/$SPORT$?sort=StartTime&req=la,l,s,tn,stnf,c,mb,mbl"

#Replace $ODD_URL$
MATCH_URL = "https://www.betano.pt/api$ODD_URL$?req=la,s,tn,stnf,c"

class Betano(WebsiteBase):
    def __init__(self,**kwargs):
        WebsiteBase.__init__(self,"Betano",**kwargs)

    #Parsing functions, all should return BetType, allways take the result returned by getMatch
    #The order has to be home_win, tie, away_win
    def parseFRBet(self,match):
        for market in match['data']['event']['markets']:
            market_name = market['name']
            market_type = market['type']
            if market_type == "MRES" or market_type == "HTOH" or market_type == "MR12" or market_type == "HHTT" or market_type == "H2HT":
                selections = []
                for bet in market['selections']:
                    bet_name = bet['name']
                    bet_odd = bet['price']
                    selections.append({"name":bet_name,"odd":bet_odd})
                return BetType(selections,match['data']['event']['url'],market_name)

        raise Exception("Error parsing FR Bet")

    #Should return a list of GameMatches
    def getMatchList(self):
        result=[]
        for match_list_endpoint,sport in SPORT_IDS.items():
            num_matches = 1
            latestID=None
            while num_matches>0:
                num_matches = 0
                if latestID ==None:
                    val = requests.get(url=MATCH_LIST_URL.replace("$SPORT$",match_list_endpoint))
                else:
                    val = requests.get(url=MATCH_LIST_URL.replace("$SPORT$",match_list_endpoint)+"&latestId="+str(latestID))

                if not val.ok:
                    print("Fail to get sport list",match_list_endpoint,"on Betano - error=",val.text)
                    break
                
                try:
                    json_data = val.json()
                    for block in json_data["data"]["blocks"]:
                        for match in block['events']:
                            latestID = match['id']
                            num_matches+=1
                            result.append(GameMatch(match['url'],sport,match['name'],match['betRadarId']))

                except Exception as e:
                    logging.warning("Error parsing sport",match_list_endpoint,"on Betano, error_message=",str(e))
            
            
        return result

    #Should return an object that will be used on parsing
    #In order to debug, should be in json format
    def getMatch(self,id):
        val = requests.get(url=MATCH_URL.replace("$ODD_URL$",id))
        #print("Queryied endpoint:",MATCH_URL.replace("$ODD_URL$",id))
        if not val.ok:
            return None

        return val.json()

    #Saves the raw event file
    def saveRawEvent(self,match_id,filename):
        match = self.getMatch(match_id)
        if match != None:
            dumpJsonFile(filename,self.getMatch(match_id))

    #Saves the raw match list file
    def saveRawMatchList(self,filename):
        pass


    def preformJsonRequest(self,url):
        val = requests.get(url=url)
        if not val.ok:
            raise Exception("Error on request",val.text)

        return val.json()


if __name__ == '__main__':
    betano = Betano()
    matches = betano.getMatchList()
    for match in matches:
        dumpJsonFile("betano_match_"+str(match.id)+".json",betano.getMatch(match.id))