from bet_pt.bet_pt_scrapper import BetPt
from betclic.betclic import BetClic
from betano.betano import Betano
from betway.betway import Betway
from copy import deepcopy
import website_base
import json,csv,os,logging
import pandas as pd

logging.basicConfig(level=logging.CRITICAL)
websites = [Betano(),BetPt(),BetClic(),Betway()]
matchesIds = []

class ArbitrageBet:
    def __init__(self,matchID,betTypeID,websiteList):
        self.selections = []
        self.matchName = ""
        self.betType = betTypeID
        self.arbitrageScore = 0.0
        for website in websiteList:
            match = website.getGameMatch(matchID)
            if match == None:
                continue
            bet = match.getBet(betTypeID)
            if bet == None:
                continue

            if len( self.selections) == 0:
                self.matchName = match.matchName
                selections = deepcopy(bet.listOdds)
                for s in selections:
                    s['website'] = website.websiteName
                self.selections = selections
                continue

            if len(bet.listOdds) != len(self.selections):
                raise Exception("Number of selection is different on matchRadarID "+str(matchID)+" website-1: "+str(self.selections[0]['website'])+" website-2: "+website.websiteName)

            for newOdd,currOdd in zip(bet.listOdds,self.selections):
                if newOdd['odd'] > currOdd['odd']:
                    currOdd['odd'] = newOdd['odd']
                    currOdd['name'] = newOdd['name']
                    currOdd['website'] = website.websiteName
        
        for selection in self.selections:
            self.arbitrageScore += 1/selection['odd']

    def isProfitableArbitrage(self):
        return self.arbitrageScore < 1

    def getProfit(self):
        return (1/self.arbitrageScore) -1


    def __str__(self):
        result = ""
        if not self.isProfitableArbitrage():
            result += "No profitable arbitrage for match " + self.matchName + " at " + self.betType + " with arbitrage score of "+ str(self.arbitrageScore)
        else: 
            result += "Profitable arbitrage with " + str(round(self.getProfit()*100,2)) + "% profit for match " + self.matchName + " at " + self.betType + "\n"
            for selection in self.selections:
                result += "\t- Option "+selection['name']+" with odd " +str(selection['odd']) + " on " + selection['website'] + " - Bet " + str(round((1/selection['odd'])/self.arbitrageScore,2)*100) +"%\n"
        return result

    def __repr__(self):
        return self.__str__()





def getProfitableArbitrageBets(ids,prepared_websites):
    list_arbitrage_bets = []
    for id in ids:
        for betType in website_base.BET_TYPE:
            try:
                list_arbitrage_bets.append(ArbitrageBet(id,betType,prepared_websites))
            except Exception as e:
                logging.error("Creating arbitrage bet "+ str(id) + " error with exception " + str(e))
    return list_arbitrage_bets

def saveRawFiles(uniqueIds,prepared_websites):
    for website in prepared_websites:
        website.saveRawMatchList(website.websiteName+"_matchList.json")
        for id in uniqueIds:
            website.saveRawEventByRadarID(id,website.websiteName+"_event_"+str(id)+".json")







for website in websites:
    website.prepareData()
    print(str(len(website.matches)) + " matches found on " +str(website.websiteName))
    matchesIds.extend(website.getAvailableMatchesIDs())

uniqueIDs = set([i for i in matchesIds if matchesIds.count(i)>1])

print("Number of common matches "+str(len(uniqueIDs)))

arbitrages = getProfitableArbitrageBets(uniqueIDs,websites)
print("Number of bets arbitrages tested " + str(len(arbitrages)))
for each in arbitrages:
    if each.isProfitableArbitrage():
        print(each)
