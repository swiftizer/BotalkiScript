import requests
from requests.structures import CaseInsensitiveDict
from time import *
import pyrebase


def process():
    # Настраиваем firebase и качаем файл uuids.txt
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

    firebase = pyrebase.initialize_app(config)
    storage = firebase.storage()
    storage.child('uuids.txt').download('uuids.txt')

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

    # Получаем html сайта с расписанием
    htmlLines = requests.Session().get(urlMain).content.decode().split('\n')
    print('Получил html с группами')

    groupsNames = []
    groupsIDs = []
    groupsSchedules = []
    allCabinets = []

    # Анализируем построчно html: если кнопка с расписанием группы зеленая
    # (то есть у группы есть расписание) - добавляем в массив валидных групп соответвующую группу
    for i, line in enumerate(htmlLines):
        if 'class="btn btn-primary text-nowrap" style="margin:1px">' in line:
            groupsNames.append(htmlLines[i+1].strip(' '))

    # Для того чтобы понять, надо ли заново вытаскивать все группы с сайта, надо проверить актуальность
    # имеющихся данных. Если мы уже выкачивали группы, то первой строкой в файле uuids.txt записана дата
    # начала текущего семестра. Мы сравниваем эту дату <oldStartDate> с той, которая сейчас на сайте <actualStartDate>,
    # и в зависимости от совпадения/несовпадения завершаем скриптос или скачиваем новые данные
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
        print('\nДанные устарели/их нет. Ну шо, го их скачаем...')
        print(f'Нада выкачать инфу про {len(groupsNames)} групп')
        print(f'\nВыкачиваю ID-шники:')
        # По именам валидных групп выкачиваем их uuids
        for i, name in enumerate(groupsNames):
            data = '{ '+f'"parent_uuid": "", "query": "{name}", "type": "group"'+'}'
            json = requests.post(urlSearch, headers=headersSearch, data=data.encode('utf-8')).json()
            groupsIDs.append(json['items'][0]['uuid'])
            sleep(0.4)
            if not i % 100:
                # печать прогресса
                print(f'{i}/{len(groupsNames)}')

        # Пишем в uuids.txt первой строкой - актуальную дату начала сема, последующими - uuids валидных групп
        with open('uuids.txt', 'w') as f:
            f.write(requests.get(urlSchedule + groupsIDs[0], headers=headersSchedule).json()['semester_start'] + '\n')
            for uuid in groupsIDs:
                f.write(uuid+'\n')

        # Заливаем на firebase
        storage.child('uuids.txt').put('uuids.txt')

        pares = {'08:30:00': 0, '10:15:00': 1, '12:00:00': 2, '13:50:00': 3, '15:40:00': 4, '17:25:00': 5, '19:10:00': 6}

        # таблицы свободных аудиторий (строка - день, столбец - пара)
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

        def unspecTimeChooser(unspecTime):
            validTimes = ['08:30:00', '10:15:00', '12:00:00', '13:50:00', '15:40:00', '17:25:00', '19:10:00']
            validTimesMinutes = [list(map(int, t.split(':')[:-1]))[0] * 60 + list(map(int, t.split(':')[:-1]))[1] for t in
                                 validTimes]
            unspecTimeMinutes = list(map(int, unspecTime.split(':')[:-1]))[0] * 60 + \
                                list(map(int, unspecTime.split(':')[:-1]))[1]
            validTimesMinutes.append(unspecTimeMinutes)
            validTimesMinutes.sort()
            ind = validTimesMinutes.index(unspecTimeMinutes)
            prevTime = validTimesMinutes[ind - 1]
            curTime = validTimesMinutes[ind]
            nextTime = validTimesMinutes[ind + 1]

            validTimesMinutes.pop(ind)
            if curTime - prevTime < nextTime - curTime:
                return validTimesMinutes.index(prevTime)
            else:
                return validTimesMinutes.index(nextTime)

        # Скачиваем расписание каждой группы
        print(f'\nВыкачиваю аудитории:')
        for i, id in enumerate(groupsIDs):
            json = requests.get(urlSchedule + id, headers=headersSchedule).json()
            # Анализируем инфу про каждую пару
            for lesson in json['lessons']:
                day = lesson['day'] - 1
                try:
                    pare = pares[lesson['start_at']]
                except:
                    # Если время начала пары нестандартное (12:20 например), то выбираем ближайшее к нему
                    pare = unspecTimeChooser(lesson['start_at'])

                cabinet = lesson['cabinet']
                is_numerator = lesson['is_numerator']
                if isCabinetSuitable(cabinet):
                    allCabinets.append(cabinet)
                    if is_numerator:
                        numeratorFreeCabinets[day][pare].append(cabinet)
                    else:
                        denominatorFreeCabinets[day][pare].append(cabinet)
            sleep(0.4)
            if not i % 100:
                print(f'{i}/{len(groupsIDs)}')

        # удаляем дублирующиеся аудитории
        allCabinets = set(allCabinets)

        # сортируем аудитории для удобства (по этажам + сначала гз, оптом улк)
        def cabinetsCmp(cab):
            if 'л' not in cab:
                return float(cab.strip('ю').strip('кк ').strip('а')) - 2000
            return float(cab.strip('л').strip('кк ').strip('а'))

        # Сейчас в numeratorFreeCabinets и в denominatorFreeCabinets лежат ЗАНЯТЫЕ аудитории. Чтоб положить
        # туда своболные - делаем разность множества всех аудиторий и занятых для конкретных дня и пары
        for day in range(len(numeratorFreeCabinets)):
            for pare in range(len(numeratorFreeCabinets[0])):
                numeratorFreeCabinets[day][pare] = sorted(list(allCabinets - set(numeratorFreeCabinets[day][pare])), key=cabinetsCmp)
                denominatorFreeCabinets[day][pare] = sorted(list(allCabinets - set(denominatorFreeCabinets[day][pare])), key=cabinetsCmp)

        # заполняем файл с результатом.
        # Структура файла:
        # 1-я строка (аудитории числителя):
        # через # - аудитории конкретной пары конкретного дня
        # после ## - аудитории следующей пары конкретного дня
        # после ### - аудитории следующего дня
        # 2-я строка (аудитории знаменателя): то же самое
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


        # Заливаем файл в firebase.storage
        storage.child('cabinets.txt').put('res.txt')
        print(f'\nЗалил на firebase актуальную инфу. Не благодари')
    else:
        print('Данные актуальны!')


if __name__ == '__main__':
    try:
        process()
    except Exception as e:
        print('Краш на серваке. Ну или мой скриптос гавно...')
        print(e)