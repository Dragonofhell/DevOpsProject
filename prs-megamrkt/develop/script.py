from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from bs4 import BeautifulSoup
import time
from datetime import datetime
import pandas as pd  # for Excel export
from urllib.parse import urlparse
from openpyxl.styles import Font


driver_path = r'E:\\geckodriver.exe'
s = Service(driver_path)
options = FirefoxOptions()
driver = webdriver.Firefox(service=s, options=options)


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
                    print('Обнаружен товар, которого нет в наличии. Завершение работы.')
                    return items_links

        page_counter += 1
    return items_links

def fetch_data_from_links(links):
    items_data = []
    for link in links:
        try:
            driver.get(link)
            time.sleep(5)  # ждем время на загрузку страницы
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            name = soup.find('div', class_="product-info-title")
            price = soup.find('span', class_="sales-block-offer-price__price-final").get_text(strip=True)
            bonus_percent = soup.find('span', class_="bonus-percent").get_text(strip=True)
            bonus_amount = soup.find('span', class_="bonus-amount").get_text(strip=True)

            # Преобразование строки цены в число, убираем пробел и рубли
            price = float(price[:-2].replace(' ', ''))

            # Преобразование строки количества бонусов и бонусов в процентах в число
            bonus_amount = int(bonus_amount.replace(' ', ''))
            bonus_percent = int(bonus_percent.replace('%', ''))

            print(f"Название: {name}, Цена: {price}, Бонусы: {bonus_percent}, Количество: {bonus_amount}")
            items_data.append({"Название": name, "Цена": price, "Бонусы": bonus_percent, "Количество": bonus_amount, "Ссылка": link})

        except Exception as e:
            print("Error in fetching data from link", link)
    return items_data

url = input("Введите ссылку на страницу: ")
links = fetch_links(url)
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


