# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from bs4 import BeautifulSoup
import time
from datetime import datetime
import pandas as pd  # for Excel export
from urllib.parse import urlparse
from openpyxl.styles import Font
import json
from random import randint


#Список агентов
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    # добавьте больше вариантов User-Agents в этот список
]

#================================ФУНКЦИИ===========================================
def load_cookies(driver, location, url=None):
    with open(location, 'r') as cookiesfile:
        cookies = json.load(cookiesfile)
        if url is not None:
            driver.get(url)
        for cookie in cookies:
            driver.add_cookie(cookie)

# Сохраняем куки
def save_cookies(driver, location):
    with open(location, 'w') as file:
        cookies = driver.get_cookies()
        json.dump(cookies, file)



def fetch_links(url):
    page_counter = 1
    items_links = []
    while True:  # Loop through each page
        if page_counter == 1:
            current_url = url
        else:
            if 'filter' in url:  # check if 'filter' is in the url
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
                link_market = item.find('div', class_="item-title").a.get('href')

                # Проверяем есть ли текст с "Самовывоз" для текущего элемента
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
    for link in links:
        attempt = 0
        while attempt < max_attempts:
            try:
                driver.get(link)
                time.sleep(randint(2,6))  # ждем время на загрузку страницы
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                name = soup.find('h1', class_="pdp-header__title pdp-header__title_only-title").get_text(strip=True)
                price = soup.find('span', class_="sales-block-offer-price__price-final").get_text(strip=True)
                bonus_percent = soup.find('span', class_="bonus-percent").get_text(strip=True)
                bonus_amount = soup.find('span', class_="bonus-amount").get_text(strip=True)

                # Преобразование строки цены в число, убираем пробел и рубли
                price = float(price[:-2].replace(' ', ''))

                # Преобразование строки количества бонусов в число
                bonus_amount = int(bonus_amount.replace(' ', ''))
                bonus_percent = int(bonus_percent.replace('%', ''))

                print(f"Название: {name}, Цена: {price}, Бонусы: {bonus_percent}, Количество: {bonus_amount}")
                items_data.append({"Название": name, "Цена": price, "Бонусы": bonus_percent, "Количество": bonus_amount,
                                   "Реальная цена":price - bonus_amount, "Ссылка": link})
                break
            except Exception as e:
                print("Товар отсутствует или получена 404 ошибка", link)
                attempt += 1
                time.sleep(1)
                ###
                current_url = BeautifulSoup(driver.page_source, 'html.parser')
                block_ip_text = current_url.find('title')
                out_of_stock = current_url.find('button', {'class': 'subscribe-button__btn btn sm out-of-stock-block__button'})

                try:
                    if "поступлении" in out_of_stock.text:
                        print("Товара нет в наличии")
                        attempt=max_attempts
                        break
                    if 'автоматические' in block_ip_text:
                        print('Вас заметили. Ждем 20 секунд')
                        time.sleep(20)
                    if current_url.find('script', text=lambda t: 'window.location.href' in t):
                        print('Обнаружен автоматический редирект. Ждем 20 секунд')
                        time.sleep(20)
                        continue
                except Exception as e:
                    print("Что-то пошло не так(возможно 404)")


        if attempt == max_attempts:
            print(f"Не удалось обработать старницу {link} after {max_attempts} попытки")

    return items_data

#==================================================================================



#Чтение из файла urls.txt
with open('urls.txt', 'r') as f:
    url_list = f.read().splitlines()

for url in url_list:
    driver_path = r'E:\\geckodriver.exe'
    s = Service(driver_path)
    user_agent = user_agents[randint(0, len(user_agents)-1)]
    options = FirefoxOptions()
    options.add_argument(f'user-agent={user_agent}')
    driver = webdriver.Firefox(service=s, options=options)
    try:  # Пытаемся загрузить куки
        load_cookies(driver, r'E:\\Programs\\PythonProject\\cookies.txt', url)
    except:  # Если не удалось загрузить, мы открываем сайт и сохраняем куки
        driver.get(url)
        save_cookies(driver, r'E:\\Programs\\PythonProject\\cookies.txt')
    links = fetch_links(url)
    data = fetch_data_from_links(links)

    # Закрываем веб-драйвер после использования
    save_cookies(driver, r'E:\\Programs\\PythonProject\\cookies.txt')

    driver.quit()
    # Получаем части URL
    parsed_url = urlparse(url)
    # Делим путь на части
    path_parts = parsed_url.path.strip("/").split("/")
    # Берем нужные из них: 'catalog' и 'televizory'
    needed_parts = path_parts[0:2]
    # Соединяем их через '-', добавляем дату и формат файла
    date_string = datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p")
    filename = "-".join(needed_parts) + date_string + ".xlsx"

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






