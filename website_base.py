import csv,json,logging
from pathlib import Path
FINAL_TIME_MATCH_RESULT ="1X2 - FINAL_TIME"

BET_TYPE = {
    FINAL_TIME_MATCH_RESULT,
}

FUTEBOL_MATCH_TYPE =  "FUTEBOL"
TENIS_MATCH_TYPE = "TENIS"
F1_MATCH_TYPE = "F1"
BASTQUETEBOL_MATCH_TYPE = "BASTQUETEBOL"
RUGBY_MATCH_TYPE = "XV RUGBY"
VOLEIBOL_MATCH_TYPE = "VOLEIBOL"
ANDEBOL_MATCH_TYPE = "ANDEBOL"
HOQUEI_GELO_MATCH_TYPE = "HOQUEI NO GELO"
FOTEBOL_AMERICANO_MATCH_TYPE = "FOTEBOL AMERICANO"
MOTOCICLISMO_MATCH_TYPE = "MOTOCICLISMO"
BASEBOL_MATCH_TYPE = "BASEBOL"
NASCAR_MATCH_TYPE = "NASCAR"
FUTSAL_MATCH_TYPE = "FUTSAL"


MATCH_TYPE = {
    FUTEBOL_MATCH_TYPE,
    TENIS_MATCH_TYPE,
    F1_MATCH_TYPE,
    BASTQUETEBOL_MATCH_TYPE,
    RUGBY_MATCH_TYPE,
    VOLEIBOL_MATCH_TYPE,
    ANDEBOL_MATCH_TYPE,
    HOQUEI_GELO_MATCH_TYPE,
    FOTEBOL_AMERICANO_MATCH_TYPE,
    MOTOCICLISMO_MATCH_TYPE,
    BASEBOL_MATCH_TYPE,
    NASCAR_MATCH_TYPE,
    FUTSAL_MATCH_TYPE
}

def dumpJsonFile(name,json_data):
    name = name.replace("/","_")
    Path("Dumps").mkdir(parents=True, exist_ok=True)
    with open("Dumps/"+name,"w") as f:
        json.dump(json_data,f,indent=4)

class GameMatch:
    #BetRadarID is an id required to compare against another bookmakers
    #matchType is a MATCH_TYPE 
    #matchName is the name of the match
    #matchID is the id of the match used request the bets later 
    def __init__(self,matchID,matchType,matchName,betRadarID,json_file=None):

        if matchType not in MATCH_TYPE:
            raise Exception("Match type unknown")
        self.id = matchID
        self.matchType = matchType
        self.matchName = matchName
        self.betRadarID = int(betRadarID)
        self.betList = {}

    #Type has to be one of bet_types
    def setBet(self,bet,type):
        if type not in BET_TYPE:
            raise Exception("Bet type unknown")
        
        self.betList[type] = bet

    def getBet(self,type):
        if type in self.betList:
            return self.betList[type]
        else:
            return None


    def __eq__(self, other):
        if isinstance(other, GameMatch):
            return self.betRadarID == self.betRadarID
        else:
            return False

    def __hash__(self):
        return hash(self.betRadarID)

    def __str__(self):
        return self.matchType +"-"+ self.matchName +" - " +str(self.betRadarID)

    def __repr__(self):
        return self.__str__()


class BetType:
    #listOdds is a list of dictionaries containing two keys, "odd" and "name", which are the selections
    #matchID is the match identifier of the bookmaker
    #name is the name of the bet
    def __init__(self,listOdds,matchID,name):      
        for odd in listOdds:
            if "odd" not in odd or "name" not in odd:
                raise Exception("listOdds must be a list of dictionaries containing an odd and a name field")
            if isinstance(odd['odd'], str):
                odd['odd'] = float(odd['odd'])

        self.name = name
        self.listOdds = listOdds
        self.matchID = matchID

    
    def __str__(self):
        market = "Bet: " + self.name + " | "
        for odd in self.listOdds:
            market += odd["name"] + "->" + str(odd['odd']) + ","
        return market

    def __repr__(self):
        return self.__str__()


class WebsiteBase:
    def __init__(self,name,debug=False):
        self.websiteName = name
        self.dataIsReady = False
        self.debug = debug


    def prepareData(self):
        self.matches = {match.betRadarID:match for match in self.getMatchList()}
        self.dataIsReady = True

    def getGameMatch(self,radarBet):
        if radarBet in self.matches:
            match = self.matches[radarBet]
            try:
                match_bets = self.getMatch(match.id)
                match.setBet(self.parseFRBet(match_bets),FINAL_TIME_MATCH_RESULT)
            except Exception as e:
                logging.warning("Error parsing parsing match "+str(match)," on " +str(self.websiteName,str(e)))
                if self.debug:
                    dumpJsonFile(self.websiteName+"_"+str(radarBet)+".json",match_bets)
            
            return match
        else:
            return None

    def getAvailableMatchesIDs(self):
        if not self.dataIsReady:
            raise Exception("prepareData needs to be called before saveAsCSV")
        return [id for id,match in self.matches.items()]

    def saveAsCSV(self):
        if not self.dataIsReady:
            raise Exception("prepareData needs to be called before saveAsCSV")
        with open(self.websiteName+'.csv', 'w',encoding='utf-8') as f: 
            write = csv.writer(f)
            write.writerow(["matchName","matchID", "matchRadarID","matchType","betType","betName","optionName1","optionOdd1","optionName2","optionOdd2","optionName3","optionOdd3"])
            for bet_id,match in self.matches.items():
                self.getGameMatch(bet_id)
                for type,bet in match.betList.items():
                    row = [match.matchName,match.id,match.betRadarID,match.matchType,type,bet.name]
                    for selection in bet.listOdds:
                        row.append(selection['name'])
                        row.append(selection['odd'])
                    write.writerow(row) 

    def saveRawEventByRadarID(self,radar_id,filename):
        if not self.dataIsReady:
            raise Exception("prepareData needs to be called first")
        if radar_id in self.matches:
            match = self.matches[radar_id]
            self.saveRawEvent(match.id,filename)

    #THIS METHODS NEEDS TO BE OVERWRITE

    #Parsing functions should return BetType instance
    #The order of the bet selections has to be home_win, tie, away_win
    def parseFRBet(self,match):
        pass



    #Must return a list of GameMatches
    def getMatchList(self):
        pass

    #Must return an object that will be used on parsing
    #In order to debug, should be in json format
    #SHould return None in case it doesn't exist
    def getMatch(self,id):
        pass

    #Saves the raw event file
    def saveRawEvent(self,match_id,filename):
        pass

    #Saves the raw match list file
    def saveRawMatchList(self,filename):
        pass
