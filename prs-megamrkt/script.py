from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from bs4 import BeautifulSoup
import time
from datetime import datetime
import pandas as pd # for Excel export
from urllib.parse import urlparse
import os

driver_path = r'E:\\geckodriver.exe'
s = Service(driver_path)
options = FirefoxOptions()
driver = webdriver.Firefox(service=s, options=options)

def fetch_data(url):
    page_counter = 1
    items_data = []
    while True: # Loop through each page
        if page_counter == 1:
            current_url = url
        else:
            if 'filter' in url: # check if 'filter' is in the url
                current_url = url.split('#')[0] + f'/page-{page_counter}/' + '#' + url.split('#')[1]  # add 'page-X/' before '#'
            else:
                current_url = url + f'/page-{page_counter}/'

        driver.get(current_url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        items = soup.find_all('div', class_="item-block")

        if not items:
            print(f"Нет товаров на странице {page_counter}. Поиск завершен.")
            break
        for item in items:
            try:
                name = item.find('div', class_="item-title").get_text(strip=True)
                price = item.find('div', class_="item-price").get_text(strip=True)
                bonus_percent = item.find('span', class_="bonus-percent").get_text(strip=True)
                bonus_amount = item.find('span', class_="bonus-amount").get_text(strip=True)
                link_market = item.find('div', class_="item-title").a.get('href')
                # Проверяем есть ли текст с "Самовывоз" для текущего элемента
                pick_up = item.find('span', {'class': 'catalog-item-delivery__text'})
                if pick_up and 'Самовывоз' in pick_up.get_text(strip=True):
                    continue
                # Преобразование строки цены в число, убираем пробел и рубли
                price = float(price[:-2].replace(' ', ''))

                # Преобразование строки количества бонусов в число
                bonus_amount = int(bonus_amount.replace(' ', ''))

                print(f"Название: {name}, Цена: {price}, Бонусы: {bonus_percent}, Количество: {bonus_amount}")
                items_data.append({"Название": name, "Цена": price,
                                   "Бонусы": bonus_percent, "Количество": bonus_amount,
                                   "Реальная цена": price - bonus_amount,
                                   "Ссылка":'https://megamarket.ru/'+link_market})
            except Exception as e:
                print ("Error Data")
        page_counter += 1
    return items_data

url = "https://megamarket.ru/catalog/vstraivaemye-posudomoechnye-mashiny-45-sm/brand-gorenje/"
#fetch_data(url)
data = fetch_data(url)

# Закрываем веб-драйвер после использования
driver.quit()
# Получаем части URL
parsed_url = urlparse(url)
# Делим путь на части
path_parts = parsed_url.path.strip("/").split("/")
# Берем нужные из них: 'catalog' и 'televizory'
needed_parts = path_parts[0:2]
# Соединяем их через '-', добавляем дату и формат файла
date_string=datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p")
filename = "-".join(needed_parts) + date_string+".xlsx"

df = pd.DataFrame(data)

df.to_excel(filename, index=False)

