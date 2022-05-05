import requests
from requests.structures import CaseInsensitiveDict
from time import *
import pyrebase
# from firebase import Firebase

urlMain = 'https://lks.bmstu.ru/schedule/list'
urlSearch = "https://api.bitop.bmstu.ru/search/unit"
urlSchedule = 'https://api.bitop.bmstu.ru/schedule/'

headersSearch = CaseInsensitiveDict()
headersSearch["accept"] = "application/json"
headersSearch["x-bb-token"] = "bb-at-bl525mhcfrndq3z7rse3m4fnd2nezr6z9t2e3hlsnlc4s"
headersSearch["Content-Type"] = "application/json"

headersSchedule = CaseInsensitiveDict()
headersSchedule["accept"] = "application/json"
headersSchedule["x-bb-token"] = "bb-at-bl525mhcfrndq3z7rse3m4fnd2nezr6z9t2e3hlsnlc4s"

# print(len(open('uuids.txt').readlines()))
# exit(0)
# with open('uuids.txt', 'a') as f:
#     f.write(requests.get(urlSchedule+'7377f733-7bf4-4416-b96f-74b190e98b03', headers=headersSchedule).json()['semester_start'] + '\n')

htmlLines = requests.Session().get(urlMain).content.decode().split('\n')
groupsNames = []
groupsIDs = []
groupsSchedules = []
allCabinets = []
# print(html)

for i, line in enumerate(htmlLines):
    if 'class="btn btn-primary text-nowrap" style="margin:1px">' in line:
        groupsNames.append(htmlLines[i+1].strip(' '))

print(len(groupsNames))

try:
    with open('uuids.txt') as f:
        oldStartDate = f.readline()
except:
    oldStartDate = None
actualStartDate = requests.get(urlSchedule+requests.post(urlSearch,
                                     headers=headersSearch,
                                     data=('{ '+f'"parent_uuid": "", "query": "{groupsNames[0]}", "type": "group"'+'}')
                                     .encode('utf-8')).json()['items'][0]['uuid'],
                                     headers=headersSchedule).json()['semester_start'] + '\n'

if oldStartDate != actualStartDate:
    for i, name in enumerate(groupsNames):
        data = '{ '+f'"parent_uuid": "", "query": "{name}", "type": "group"'+'}'
        json = requests.post(urlSearch, headers=headersSearch, data=data.encode('utf-8')).json()
        groupsIDs.append(json['items'][0]['uuid'])
        sleep(0.4)
        if not i % 10:
            # print(i, len(groupsIDs), groupsIDs)
            print(f'{i}/{len(groupsNames)}')

    with open('uuids.txt', 'w') as f:
        f.write(requests.get(urlSchedule + groupsIDs[0], headers=headersSchedule).json()['semester_start'] + '\n')
        for uuid in groupsIDs:
            f.write(uuid+'\n')

    with open('uuids.txt') as f:
        groupsIDs = [id.strip('\n') for id in f.readlines()[1:]]

    # print(requests.get(urlSchedule + groupsIDs[0], headers=headersSchedule).json())

    # таблицы свободных аудиторий (строка - день, столбец - пара)
    pares = {'08:30:00': 0, '10:15:00': 1, '12:00:00': 2, '13:50:00': 3, '15:40:00': 4, '17:25:00': 5, '19:10:00': 6}
    numeratorFreeCabinets = [[[] for _ in range(7)] for _ in range(6)]
    denominatorFreeCabinets = [[[] for _ in range(7)] for _ in range(6)]

    def isCabinetSuitable(cab):
        if 'л' in cab or 'ю' in cab:
            return 1
        try:
            float(cab.strip('кк '))
            return 1
        except:
            return 0

    for i, id in enumerate(groupsIDs):
        json = requests.get(urlSchedule + id, headers=headersSchedule).json()
        for lesson in json['lessons']:
            day = lesson['day'] - 1
            try:
                pare = pares[lesson['start_at']]
            except:
                pare = 0  # оч стремный момент
            cabinet = lesson['cabinet']
            is_numerator = lesson['is_numerator']
            if isCabinetSuitable(cabinet):
                allCabinets.append(cabinet)
                if is_numerator:
                    numeratorFreeCabinets[day][pare].append(cabinet)
                else:
                    denominatorFreeCabinets[day][pare].append(cabinet)
        # groupsSchedules.append(json)
        sleep(0.4)
        if not i % 10:
            print(i, len(set(allCabinets)), set(allCabinets))
        # if not (i + 1) % 40:
        #     break

    allCabinets = set(allCabinets)

    def cabinetsCmp(cab):
        if 'л' not in cab:
            return float(cab.strip('ю').strip('кк ').strip('а')) - 2000
        return float(cab.strip('л').strip('кк ').strip('а'))

    for day in range(len(numeratorFreeCabinets)):
        for pare in range(len(numeratorFreeCabinets[0])):
            numeratorFreeCabinets[day][pare] = sorted(list(allCabinets - set(numeratorFreeCabinets[day][pare])), key=cabinetsCmp)
            denominatorFreeCabinets[day][pare] = sorted(list(allCabinets - set(denominatorFreeCabinets[day][pare])))

    with open('res.txt', 'w') as f:
        for day in range(len(numeratorFreeCabinets)):
            for pare in range(len(numeratorFreeCabinets[0])):
                f.write('#'.join(numeratorFreeCabinets[day][pare])+('##' if pare != len(numeratorFreeCabinets[0])-1 else ''))
            f.write('###') if day != len(numeratorFreeCabinets)-1 else f.write('')
        f.write('\n')

        for day in range(len(denominatorFreeCabinets)):
            for pare in range(len(denominatorFreeCabinets[0])):
                f.write('#'.join(denominatorFreeCabinets[day][pare])+('##' if pare != len(denominatorFreeCabinets[0])-1 else ''))
            f.write('###') if day != len(denominatorFreeCabinets)-1 else f.write('')


with open('res.txt') as f:
    numeratorFreeCabinets = [[pare.split('#') for pare in day.split('##')] for day in f.readline().strip('\n').split('###')]
    denominatorFreeCabinets = [[pare.split('#') for pare in day.split('##')] for day in f.readline().split('###')]


print("after")
# print(requests.get(urlSchedule+'7377f733-7bf4-4416-b96f-74b190e98b03', headers=headersSchedule).json())
# print(numeratorFreeCabinets, denominatorFreeCabinets)
# print(resp.json())

config = {
    "apiKey": "AIzaSyBB0Rc45M5ioYI2uH8wNuZ37IxS0UA7e64",
    "authDomain": "botalki.firebaseapp.com",
    "databaseURL": "gs://botalki.appspot.com",
    "projectId": "botalki",
    "storageBucket": "botalki.appspot.com",
    "messagingSenderId": "1078676302571",
    "appId": "1:1078676302571:web:3b94f33569a53a64452cae",
    "measurementId": "G-TB9KDEX6XW"
}

# firebase = Firebase(config)
firebase = pyrebase.initialize_app(config)
storage = firebase.storage()

storage.child('cabinets.txt').put('res.txt')