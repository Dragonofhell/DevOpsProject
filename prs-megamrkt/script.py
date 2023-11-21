# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup
import time
from datetime import datetime
import pandas as pd  # for Excel export
from urllib.parse import urlparse
from openpyxl.styles import Font
import json
import random
from random import randint
import requests
import os

#================================ФУНКЦИИ===========================================
#Загрузка config.json!
def load_config():
    with open('config/config.json', 'r') as f:
        return json.load(f)
config = load_config()

#Объявляем переменные для использования в коде
tokenid_top = config.get('tokenid_top')
tokenid = config.get('tokenid')
result_dir = config.get('result_dir')
chat_id = str(config.get('chat_id'))
min_bonus_amount = config.get('min_bonus_amount')
best_bonus_amount = config.get('best_bonus_amount')
telegram_status = config.get('telegram_enable')

# Если в файле config.json значение tokenid_top пустое либо отсутствует, используем значение tokenid
if not tokenid_top:
    tokenid_top = tokenid

def fetch_links(url):
    page_counter = 1
    items_links = []
    while True:
        if page_counter == 1:
            current_url = url
        else:
            if 'filter' in url:
                current_url = url.split('#')[0] + f'/page-{page_counter}/' + '#' + url.split('#')[1]  # add 'page-X/' before '#'
            else:
                current_url = url + f'/page-{page_counter}/'

        driver.get(current_url)
        #load page
        time.sleep(10)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        items = soup.find_all('div', class_="item-block")

        if not items:
            count_item = len(items)
            print(f"Нет товаров на странице {page_counter}. Поиск завершен.Количество ссылок - {count_item}")
            break
        for item in items:
            try:
                link_market = item.find('div', class_="item-title").a.get('href')
                # Не добавляем товары с типом доставки "Самовывоз"
                pick_up = item.find('span', {'class': 'catalog-item-delivery__text'})
                if pick_up and 'Самовывоз' in pick_up.get_text(strip=True):
                    continue
                items_links.append('https://megamarket.ru' + link_market)
            except Exception as e:
                print("Error in fetching links")
                similar_button = item.find('div', class_='out-of-stock__footer')

                if similar_button and 'Похожие' in similar_button.get_text(strip=True):
                    print(f'В списке найден товар со статусом "Нет в наличии".  Переход к перебору цен.')
                    #Cчитаем количество ссылок
                    count_items = len(items_links)
                    print(f"Количество добавленных ссылок на товар: {count_items}")
                    return items_links
        page_counter += 1

    return items_links


def fetch_data_from_links(links):
    items_data = []
    max_attempts = 3
    captcha_url = 'https://megamarket.ru/xpvnsulc/'
    profileff = webdriver.FirefoxProfile()
    ff_options = Options()
    ff_options.profile = profileff
    driver=webdriver.Firefox(options=ff_options)
    for link in links:
        attempt = 0
        while attempt < max_attempts:
            try:
                driver.get(link)
                time.sleep(1)
                current_url = driver.current_url
                if current_url.startswith(captcha_url):
                    print('Сработала защита от скрепинга. Подождем и попробуем снова...')
                    time.sleep(50)
                    driver.quit()
                    profileff = webdriver.FirefoxProfile()
                    ff_options = Options()
                    ff_options.profile = profileff
                    driver = webdriver.Firefox(options=ff_options)
                    continue
                time.sleep(randint(2,6))  # ждем время на загрузку страницы
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                name = soup.find('h1', class_="pdp-header__title pdp-header__title_only-title").get_text(strip=True)
                price = soup.find('span', class_="sales-block-offer-price__price-final").get_text(strip=True)
                bonus_percent =''
                bonus_amount=''
                # Парсим страницу для понимания, какой кешбек брать ( оплата по сберпей, без сперпей или кешбека вообще нет)
                try:
                    element = soup.find('div', class_='pdp-cashback-table__money-bonus money-bonus xs money-bonus_loyalty')
                    if element:
                        bonus_percent = element.find('span', class_='bonus-percent').text
                        bonus_amount = element.find('span', class_='bonus-amount').text
                    else:
                        element = soup.find('div', class_='money-bonus xs money-bonus_loyalty pdp-cashback-table__money-bonus')
                        if element:
                            bonus_percent = element.find('span', class_='bonus-percent').text
                            bonus_amount = element.find('span', class_='bonus-amount').text
                        else:
                            bonus_percent = '0%'
                            bonus_amount = '0'
                except Exception as e:
                    print("Не удалось вычислить кешбек")
                # Преобразование строки цены в число, убираем пробел и рубли
                price = float(price[:-2].replace(' ', ''))
                # Преобразование строки количества бонусов в число
                bonus_amount = int(bonus_amount.replace(' ', ''))
                bonus_percent = int(bonus_percent.replace('%', ''))

                print(f"Название: {name}, Цена: {price}, Бонусы: {bonus_percent}, Количество: {bonus_amount}")
                items_data.append({"Название": name, "Цена": price, "Бонусы": bonus_percent, "Количество": bonus_amount,
                                   "Реальная цена":price - bonus_amount, "Ссылка": link})
                try:
                    if int(bonus_percent) >= min_bonus_amount and telegram_status == True:
                        if int(bonus_percent) >= best_bonus_amount:
                            token = tokenid_top
                            message = f"Название: {name}, Бонусы: {bonus_percent}, Ссылка: {link}"
                            send_text = 'https://api.telegram.org/bot' + token + '/sendMessage?chat_id=' + chat_id + '&text=' + message
                            response = requests.get(send_text)
                            # Простая проверка, успешно ли было отправлено сообщение:
                            if response.status_code != 200:
                                raise ValueError(f"Request to telegram returned an error {response.status_code}, the response is:\n{response.text}")
                        else:
                            token = tokenid
                            message = f"Название: {name}, Бонусы: {bonus_percent} %, Ссылка: {link}"
                            send_text = 'https://api.telegram.org/bot' + token + '/sendMessage?chat_id=' + chat_id + '&text=' + message
                            response = requests.get(send_text)
                            # Простая проверка, успешно ли было отправлено сообщение:
                            if response.status_code != 200:
                                raise ValueError(f"Request to telegram returned an error {response.status_code}, the response is:\n{response.text}")
                except Exception as e:
                    print(f"Не удалось отправить в телегу. Ошибка: {str(e)}")
                break
            except Exception as e:
                print("Товар отсутствует или получена 404 ошибка", link)
                attempt += 1
                time.sleep(1)
                current_url = BeautifulSoup(driver.page_source, 'html.parser')
                out_of_stock = current_url.find('button', {'class': 'subscribe-button__btn btn sm out-of-stock-block__button'})

                try:
                    if "поступлении" in out_of_stock.text:
                        print("Товара нет в наличии")
                        attempt=max_attempts
                        break
                except Exception as e:
                    print("Что-то пошло не так(возможно 404)")
        if attempt == max_attempts:
            print(f"Не удалось обработать страницу {link} after {max_attempts} попытки")
    driver.quit()
    return items_data
#=========================================ЗАКРЫТИЕ БЛОКА ФУНКЦИИ===================================



#Чтение из файла urls.txt
with open('config/urls.txt', 'r') as f:
    url_list = f.read().splitlines()

for url in url_list:
    profileff = webdriver.FirefoxProfile()
    ff_options = Options()
    ff_options.profile = profileff
    driver=webdriver.Firefox(options=ff_options)
    links = fetch_links(url)
    driver.quit()
    data = fetch_data_from_links(links)

    # Закрываем веб-драйвер после использования
    driver.quit()
    # Получаем части URL
    parsed_url = urlparse(url)
    # Делим путь на части
    path_parts = parsed_url.path.strip("/").split("/")
    # Берем нужные из них: 'catalog' и 'televizory'
    needed_parts = path_parts[0:2]
    # Соединяем их через '-', добавляем дату и формат файла
    date_string = datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p")
    filename = result_dir + "-".join(needed_parts) + date_string + ".xlsx"

    # Сохраняем DataFrame в файл Excel
    df = pd.DataFrame(data)
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)

        # Получаем активный лист
        sheet = writer.sheets['Sheet1']
        # Добавляем гиперссылки в столбце "Ссылка"
        for i, link in enumerate(df['Ссылка'], start=2):
            cell = sheet.cell(row=i, column=len(df.columns))
            cell.value = '=HYPERLINK("%s", "%s")' % (link, link)
            cell.font = Font(color="0563C1", underline="single")
