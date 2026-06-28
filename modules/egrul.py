import requests
import json
import pdfplumber
import pandas as pd
import os
import asyncio
import polars as pl
import gc
from modules.company import *
from loguru import logger
from modules.google import *
import urllib3
from urllib3.exceptions import InsecureRequestWarning


# from requests.packages.urllib3.exceptions import InsecureRequestWarning
# requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

urllib3.disable_warnings(InsecureRequestWarning)

async def get_egrul(cls = Company):
    """
    Скачивание выписки ЕГРЮЛ в папку data/inn/
    """
    
    s = requests.Session()
    s.verify = False

    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Referer": "https://egrul.nalog.ru/index.html"}

    logger.info("Отправляем GET-запрос на egrul.nalog.ru")
    r = s.get("https://egrul.nalog.ru/index.html", headers=headers)
    logger.info(f"Ответ GET-запроса: {r.status_code}")

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
    logger.info("Отправляем POST-запрос...")
    r = s.send(r)
    logger.info(f"Ответ POST-запроса: {r.status_code}, текст: {r.text[:200]}...")

    try:
        t = json.loads(r.text)['t']
        logger.info(f"Получен токен t: {t}")
    except Exception as e:
        logger.error("Ошибка при парсинге токена t из ответа POST-запроса", exc_info=True)
        return

    # await asyncio.sleep(0.5)

    logger.info("Отправляем запрос на получение search-result")
    r = s.get(f"https://egrul.nalog.ru/search-result/{t}", headers=headers)
    logger.info(f"Ответ search-result: {r.status_code}, текст: {r.text[:200]}...")

    try:
        jsn = json.loads(r.text)
    except Exception:
        logger.exception("Ошибка при разборе JSON из search-result")
        return

    try:
        if jsn['status'] == 'wait':
            await asyncio.sleep(1)
    except Exception:
        pass
    logger.info('Ответ из ЕГРЮЛ')
    if 'rows' in jsn:
        pass
    else:
        logger.info(jsn)
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

'''
async def make_card(cls = Company):
    """
    Создание карточки компании из выписки ЕГРЮЛ. Карточка будет дополняться в следующих функциях.

    """
    try:
        pdf = pdfplumber.open(cls.filename)
        pages = pdf.pages
        df1 = pd.DataFrame()

        logger.info(f"PDF состоит из {len(pages)} страниц")

        for i in range(len(pages)):
            page = pdf.pages[i]
            df = pd.DataFrame(page.extract_table(), columns=['a', 'b', 'c'])
            df1 = pd.concat([df1, df])
        
        logger.info(f"Датафрейм состоит из {len(df1)} строк")
        """
        for i in range(30):
            logger.info(f"{i} строка -- значение {df1.loc[i, 'b']}")
        """
        fio = 'Фамилия\nИмя\nОтчество'

        if len(df1.loc[df1['b'] == fio])>0:
            ceo = df1.loc[df1['b'] == fio]
        else:
            ceo = df1.loc[df1['b'] == 'Фамилия\nИмя']
        
        logger.info(f"Датафрейм ceo состоит из {len(ceo)} строк")

        logger.info("Штаб-квартира"+df1.loc[df1['b'] == 'Адрес юридического лица']['c'].str.replace('\n', ' ').values[0])
        logger.info("CEO компании"+ceo['c'].str.replace('\n', ' ').values[0])
        logger.info("Объём финансирования"+df1.loc[df1['b'] == 'Размер (в рублях)']['c'].str.replace('\n', ' ').values.sum())
        logger.info("Основной вид деятельности"+df1.loc[df1['b'] == 'Код и наименование вида деятельности']['c'].str.replace('\n', ' ').values[0])
        
        cls.card = {"Дата регистрации компании": '',
        "Штаб-квартира": df1.loc[df1['b'] == 'Адрес юридического лица']['c'].str.replace('\n', ' ').values[0],
        "CEO компании": ceo['c'].str.replace('\n', ' ').values[0],
        "Объём финансирования": df1.loc[df1['b'] == 'Размер (в рублях)']['c'].str.replace('\n', ' ').values.sum(),
        "Основной вид деятельности": df1.loc[df1['b'] == 'Код и наименование вида деятельности']['c'].str.replace('\n', ' ').values[0],
        "Юридическое лицо": df1.loc[df1['b'] == 'Полное наименование на русском языке']['c'].str.replace('\n', ' ').values[0]}
        
    except Exception as er:
        logger.error(er)
    try:
        cls.card['Дата регистрации компании'] = df1.loc[df1['b'] == 'Дата регистрации до 1 июля 2002 года']['c'].values[0]
    except Exception as er:
        #logger.error(er)
        try:
            cls.card['Дата регистрации компании'] = df1.loc[df1['b'] == 'Дата регистрации']['c'].values[0]
        except Exception as er:
            logger.error(er)

    cls.org_name = df1['c'][6].values[0].replace('\n','')
    cls.org_name = cls.org_name.replace('\"', '')
    # .replace('ООО', '').replace('ЗАО', '').replace('ОАО', '').replace('АО', '').replace('ПАО', '')
    logger.info("Юридическое лицо - " + cls.org_name)
    return cls
'''

# 08.10.2025 - оптмизируем make_card

async def make_card(cls=Company):
    """
    Создание карточки компании из выписки ЕГРЮЛ. 
    Карточка будет дополняться в следующих функциях.
    Обрабатывает PDF постранично, не держит весь файл в памяти.
    """

    needed_keys = {
        "Адрес юридического лица": "Штаб-квартира",
        "Размер (в рублях)": "Объём финансирования",
        "Код и наименование вида деятельности": "Основной вид деятельности",
        "Полное наименование на русском языке": "Юридическое лицо",
        "Дата регистрации до 1 июля 2002 года": "Дата регистрации компании",
        "Дата регистрации": "Дата регистрации компании"
    }

    results = {v: None for v in needed_keys.values()}
    ceo_value = None 

    try:
        logger.info(f"Создаем карточку компании")
        with pdfplumber.open(cls.filename) as pdf:
            logger.info(f"PDF состоит из {len(pdf.pages)} страниц")

            for page in pdf.pages:
                table = page.extract_table()
                if not table:
                    continue

                df = pl.DataFrame(table, schema=["a", "b", "c"])

                if ceo_value is None:
                    ceo_rows = df.filter(pl.col("b") == "Фамилия\nИмя\nОтчество")
                    if ceo_rows.height > 0:
                        ceo_value = ceo_rows["c"][0].replace("\n", " ").strip()
                    else:
                        ceo_rows = df.filter(pl.col("b") == "Фамилия\nИмя")
                        if ceo_rows.height > 0:
                            ceo_value = ceo_rows["c"][0].replace("\n", " ").strip()

                matches = df.filter(pl.col("b").is_in(list(needed_keys.keys())))

                for row in matches.iter_rows(named=True):
                    key = row["b"]
                    val = (row["c"] or "").replace("\n", " ").strip()
                    mapped_key = needed_keys[key]
                    if not results[mapped_key]:
                        results[mapped_key] = val

                del df, matches, table, page
                gc.collect()

                # если нашли всё, можно выйти
                if all(results.values()) and ceo_value:
                    logger.info(f"Все данные найдены, прекращаем чтение PDF.")
                    break

            logger.info(f"Извлечено полей: {sum(1 for v in results.values() if v)} из {len(results)}")

        # Добавляем CEO в результаты
        results["CEO компании"] = ceo_value or "Не указано"

        # постобработка — сумма финансирования
        if results["Объём финансирования"]:
            try:
                results["Объём финансирования"] = str(sum(
                    float(x.replace(" ", "").replace(",", ".")) 
                    for x in results["Объём финансирования"].split()
                    if x.replace(",", ".").replace(".", "", 1).isdigit()
                ))
            except Exception:
                pass

        cls.card = results

        # Название компании
        org_name = results.get("Юридическое лицо", "")
        if not org_name:
            logger.warning("Юридическое лицо не найдено, пробуем взять из первых строк PDF")

            # fallback — прочитаем первые 5 строк первой страницы
            with pdfplumber.open(cls.filename) as pdf:
                first_page = pdf.pages[0]
                table = first_page.extract_table()
                if table and len(table) > 6:
                    org_name = table[6][2].replace("\n", "").replace('"', "")
                del table, first_page
                gc.collect()
        
        cls.org_name = org_name
        logger.info(f"Юридическое лицо - {cls.org_name}")

        return cls

    except Exception as er:
        logger.exception(f"Ошибка в make_card: {er}")
        gc.collect()
        return cls