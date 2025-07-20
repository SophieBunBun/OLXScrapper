from urllib.request import urlopen
from bs4 import BeautifulSoup as bsoup
import geocoder
from geopy import Nominatim
from geopy.distance import geodesic
import re
import time
import os

class Loc:
    def __init__(self, lat, lng):
        self.lat = lat
        self.lng = lng

    def latlng(self):
        return (self.lat, self.lng)
        

settings = dict()
nom = Nominatim(user_agent="olx-scrapper")
locationDict = dict()

for line in open("cache", "r", encoding="ISO-8859-15").read().split('\n'):
    data = line.replace("(", "").replace(")", "").split(";")
    if (len(data) > 1):
        locationDict[data[0]] = Loc(float(data[1].split(",")[0]), float(data[1].split(",")[1]))


conv = lambda inp : inp[1:-1] if inp[0] == '"' else int(inp)
convPlus = lambda inp : [convPlus(res) for res in re.split(r',(?![^\[\]]*\])', inp[1:-1])] if inp[0] == '[' else conv(inp)
for line in open("settings.txt").read().split('\n'):
    vals = line.split('=')
    if (len(vals) > 1):
        settings[vals[0]] = convPlus(vals[1])

myLoc = nom.geocode(settings["baseLoc"])
time.sleep(2)

cycle = 1

while(True):

    print("Starting cycle " + str(cycle))
    results = list()

    for searchTerm in settings["searches"]:
        print("Searching for " + searchTerm[0])
        words = searchTerm[0].lower().replace(" ", "|")
        antiWords = settings["globalFilter"].lower().replace(" ", "|")
        antiWords += "|" + searchTerm[1].lower().replace(" ", "|") if len(searchTerm) > 1 else ""
        page = 1
        run = True
        result = list()
        dataSoup = bsoup(urlopen(settings["baseLink"] + "q-" + searchTerm[0].replace(' ', '-') + "/"), features="html.parser")
        while (run):

            print("Going through page  " + str(page))
            for listing in dataSoup.find_all(name="div", attrs={'data-testid': "l-card"}):
                title = listing.find(name="h4").get_text()
                if (re.findall(words, title.lower()) and not (re.findall(antiWords, title.lower()))):
                    adPrice = listing.find(name="p", attrs={'data-testid': "ad-price"})
                    locNDate = listing.find(name="p", attrs={'data-testid': "location-date"}).get_text().split(" - ")
                    locKey = re.sub("[(].*[)]", "", locNDate[0])

                    if (locKey not in locationDict):
                        locDat = nom.geocode(locKey)
                        locationDict[locKey] = Loc(locDat.latitude, locDat.longitude)
                        wFile = open("cache", "a", encoding="ISO-8859-15")
                        wFile.write(locKey + ";" + str(locationDict[locKey].latlng()) + "\n")
                        wFile.close()
                        time.sleep(2)

                    distance = geodesic(locationDict[locKey].latlng(), (myLoc.latitude, myLoc.longitude))
                    if (distance < settings["maxDist"] and adPrice.getText() != "Troca"):
                        
                        priceData = [float(adPrice.get_text(separator="||").split("||")[0][:-2].replace('.', '').replace(',', '.')), adPrice.find(name="span").get_text()]
                        adInfo = [title, listing.find(name="div", attrs={'type': "list"}).find(name="a")["href"]]
                        adLocDate = [distance, locNDate[0], locNDate[1]]

                        data = [priceData, adInfo, adLocDate]

                        canAdd = True
                        for item in result:
                            if (item[1][0] == data[1][0]):
                                canAdd = False
                        
                        if (canAdd):
                            result.append(data)
                            result.sort(key=lambda i : i[0][0])
                            if len(result) > settings["maxTrack"]:
                                result = result[:-1]

            if (dataSoup.find(name="a", attrs={'data-testid': "pagination-forward"})):
                page += 1
            else:
                run=False
            dataSoup = bsoup(urlopen(settings["baseLink"] + "q-" + searchTerm[0].replace(' ', '-') + "/?page=" + str(page)), features="html.parser")

        results.append([searchTerm, result])


    print("Writting data")
    strToWrite = ""

    for item in results:
        strToWrite += "\"" + item[0][0] + "\"" + "\n"
        for data in item[1]:
            strToWrite += "\"" + str(data[1][0]) + "\"" + "," + "\"" + str(data[0][0]) + "\"" + "," + "\"" + str(data[0][1]) + "\"" + "," + "\"" + str(data[2][0]) + "\"" + "," + "\"" + str(data[2][1]) + "\"" + "," + "\"" + str(data[2][2]) + "\"" + "," + "\"" + "https://www.olx.pt/" + str(data[1][1]) + "\"" + "\n"

        strToWrite += "\n\n"

    knownMax = 0
    knownMin = 99999999
    count = 0
    names = os.listdir(path='./output')
    for name in names:
        if (re.findall(settings["output"], name)):
            if (name.split("-")[1][:-4].isdigit()):
                num = int(name.split("-")[1][:-4])
                if (num > knownMax):
                    knownMax = num
                if (num < knownMin):
                    knownMin = num
                count += 1

    if (count > settings["maxFiles"]):
        os.remove("./output/" + settings["output"] + "-" + str(knownMin) + ".csv")

    wFile = open("./output/" + settings["output"] + "-" + str(knownMax + 1) + ".csv", "w")
    wFile.write(strToWrite)
    wFile.close()
    wFile = open("./output/latest.csv", "w")
    wFile.write(strToWrite)
    wFile.close()

    print("Finishing cycle " + str(cycle))
    cycle += 1

    time.sleep(settings["interval"] * 60)




