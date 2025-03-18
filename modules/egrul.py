import requests
import json
import pdfplumber
import pandas as pd
import os
import asyncio
from modules.company import *
from loguru import logger
from modules.google import *

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


async def get_egrul(cls = Company):
    """
    Скачивание выписки ЕГРЮЛ в папку data/inn/
    """
    
    s = requests.Session()
    s.verify = False

    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Referer": "https://egrul.nalog.ru/index.html"}

    r = s.get("https://egrul.nalog.ru/index.html", headers=headers)

    data = f'vyp3CaptchaToken=&page=&query={cls.inn}&region=&PreventChromeAutocomplete='
    req = requests.Request(
        'POST',
        'https://egrul.nalog.ru/',
        data=data,
        headers = {
        "Host": "egrul.nalog.ru",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://egrul.nalog.ru/index.html",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest"
        }
        )
    r = s.prepare_request(req)
    r = s.send(r)
    t = json.loads(r.text)['t']

    # await asyncio.sleep(0.5)

    r = s.get("https://egrul.nalog.ru/search-result/"+str(t), headers=headers)

    jsn = json.loads(r.text)

    try:
        if jsn['status'] == 'wait':
            await asyncio.sleep(1)
    except Exception:
        pass

    try:
        item = (jsn["rows"])[0]
        if str(item['tot']) != '0':
            t = str(item['t'])
            r = s.get("https://egrul.nalog.ru/vyp-request/"+t, headers=headers)
            await asyncio.sleep(1)
            # ждём готовности файла для дальнейшей загрузки
            while True:
                r = s.get("https://egrul.nalog.ru/vyp-status/"+t, headers=headers)
                if json.loads(r.text)['status'] == 'ready': 
                    break
                await asyncio.sleep(0.5)
            # загрузка пдф
            r = s.get("https://egrul.nalog.ru/vyp-download/"+t, headers=headers)
            cls.resources.append(r.url)
            
            if not os.path.exists(f'data/{cls.inn}/'):
                os.makedirs(f'data/{cls.inn}/')
            with open(cls.filename,'wb+') as file:
                file.write(r.content)
            logger.info(f'Выписка из ЕГРЮЛ сохранена - {cls.filename}')
    except Exception as e:
        logger.exception(e)
    return cls


async def make_card(cls = Company):
    """
    Создание карточки компании из выписки ЕГРЮЛ. Карточка будет дополняться в следующих функциях.

    """
    try:
        pdf = pdfplumber.open(cls.filename)
        pages = pdf.pages
        df1 = pd.DataFrame()

        for i in range(len(pages)):
            page = pdf.pages[i]
            df = pd.DataFrame(page.extract_table(), columns=['a', 'b', 'c'])
            df1 = pd.concat([df1, df])
            
        cls.card = {"Дата регистрации компании": '',
        "Штаб-квартира": df1.loc[df1['b'] == 'Адрес юридического лица']['c'].str.replace('\n', ' ').values[0],
        "CEO компании": df1.loc[df1['b'] == 'Фамилия\nИмя\nОтчество']['c'].str.replace('\n', ' ').values[0],
        "Объём финансирования": df1.loc[df1['b'] == 'Размер (в рублях)']['c'].str.replace('\n', ' ').values.sum(),
        "Основной вид деятельности": df1.loc[df1['b'] == 'Код и наименование вида деятельности']['c'].str.replace('\n', ' ').values[0],
        "Юридическое лицо": df1.loc[df1['b'] == 'Полное наименование на русском языке']['c'].str.replace('\n', ' ').values[0]}
    except Exception as er:
        logger.error(er)
    try:
        cls.card['Дата регистрации компании'] = df1.loc[df1['b'] == 'Дата регистрации до 1 июля 2002 года']['c'].values[0]
    except Exception as er:
        logger.error(er)
        try:
            cls.card['Дата регистрации компании'] = df1.loc[df1['b'] == 'Дата регистрации']['c'].values[0]
        except Exception as er:
            logger.error(er)
    cls.org_name = df1['c'][6].values[0].replace('\n','')
    cls.org_name = cls.org_name.replace('\"', '')
    # .replace('ООО', '').replace('ЗАО', '').replace('ОАО', '').replace('АО', '').replace('ПАО', '')
    logger.info("Юридическое лицо - " + cls.org_name)
    return cls

