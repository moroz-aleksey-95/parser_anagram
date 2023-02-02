import pandas as pd
import requests
import bs4
import time

from selenium import webdriver
from fake_useragent import UserAgent
from selenium.webdriver.common.keys import Keys
from cookies import cookies, headers


#функция проверяет доступность сайта
def connect(catalog_url):
  response = requests.get(catalog_url, cookies=cookies, headers=headers)
  if response.status_code == 200:
    return 200
  else:
    return 400


#Функция формирует список уникальных страниц в наигации
def get_page_list(url, nav, method):

  nav_list = [] #список для ссылок на страницы
  fist_page = url + nav + str(1) #первая страница
  nav_list.append(fist_page) # Добавялем в список первую ссылку на первую страиницу

  #Получаем название первого товара и сохраняем.
  #Далее он нам пригодиться для выявления выдачи сервером первой страницы при запросе к несуществующей
  response1 = requests.get(fist_page, cookies=cookies, headers=headers)
  soup1 = bs4.BeautifulSoup(response1.text, features='html.parser')

  #Выбор для какого сайта мы применям функцию.
  if method == 1:
    tag = 'h5'
    class_= 'single-card__headline'

  elif method == 2:
    tag = 'a'
    class_ = 'goods_name'

  name1 = soup1.find_all(tag, class_ = class_)

  #если есть найдены товары
  if name1 != []:
    i = 2
    while True: #В бескончном цикле выполняем запрос к станицам и проверяем ее на уникальность по первому товару
      page = url + nav + str (i) #страница по номеру i, начинаем с второй стр.
      response = requests.get(page, cookies=cookies, headers=headers) #запрос
      soup = bs4.BeautifulSoup(response.text, features='html.parser') #преобразуем в объект bs4
      name = soup.find_all(tag, class_ = class_) #Получаем название или ссылку с товара

      #Если первый товар на данной странице не равен первому товару с первой стр.,
      #то добаляем ссылку на страницу в список уникальных
      if method == 1:
        if name1[0].text != name[0].text:
          nav_list.append(page)
        #Иначе завершаем цикл. т.к. сервер нам начал выдавать контент первой стрнице вместо 404
        else:
          print('Уникальных страниц в разделе: ', i-1)
          break
        i += 1
      elif method == 2:
        if name1[0].get('href') != name[0].get('href'):
          nav_list.append(page)
        # Иначе завершаем цикл
        else:
          print('Уникальных страниц в разделе: ', i - 1)
          break
        i += 1

    return nav_list

  else:
    print('Товаров в разделе нет')
    return 400


#Прокрутит страницу до низу и плавно вверх
def scroll_page(driver):
  step = 1
  while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / %s);" % step)
    step += 0.05
    if step > 100:
      break




#Функция ищет в объекте Bs4 нужный нам параметр. Если он там есть то вернёт его индекс. Если нет, то вернёт -1
#т.к. некоторые параметры могут отствовать у товаров, илиони могут быть в разном порядке
def find_pr(pr1,title):
  for i in range(0, len(pr1)):
    if str(pr1[i].text).find(title, 0, -1) == 0:
      index = i
      break
    else:
      index = -1
  return index

def add_in_df_usa(df,name, tm, helium, mwr, max, inflated,img):
  print("записываю товар- \n", name[5: ].replace('в„ў', ''))
  #определяем кол-во записей
  index = len(df.index) + 1
  df.loc[index, 'Код'] = name[0:5]
  df.loc[index, 'Товар'] = name[5: ].replace('в„ў', '')
  df.loc[index, 'Helium Volume'] = helium.replace('Helium Volume: ', '')
  df.loc[index, 'Minimum Weight Requirement'] = mwr.replace('Minimum Weight Requirement (in Grams):  ', '')
  df.loc[index, 'Maximum Elevation'] = max.replace('Maximum Elevation (in Feet):  ', '')
  df.loc[index, 'Inflated Size'] = inflated.replace('Inflated Size (WxH in Inches and CM):  ', '')
  df.loc[index, 'img'] = img.replace('?q=100&x.template=y', '')
  df.loc[index, 'TM'] = tm.replace('в„ў', '')

  df.to_csv(r'parse_usa.csv')


def add_in_df_rus(df,name, art, code, j):
  print('В файл добавлен',j+1,'товар')
  print(name.text, 'Арт: ',art.text, 'Штрих-код', code, 'Код', code[-6: -1])

  df.loc[j, 'Артикул рус.'] = art.text
  df.loc[j, 'Название'] = name.text
  df.loc[j, 'Штрих-код'] = code
  df.loc[j, 'Код'] = code[-6: -1]

  df.to_csv(r'parse_rus.csv')


#Функция открывает в браузере страницу для пасрсинга товаров
def open_category(df,nv):
  print('Собираю товары с старницы', nv, '\n')

  useragent = UserAgent()
  # опции
  options = webdriver.ChromeOptions()  # создаём объект
  options.add_argument(f"user-agent={useragent.random}")  # добавляем юзер агент из fake_useragent рандомный
  options.add_argument("--disable-blink-features=AutomationControlled") #Откл. режима работы веб-драйвера.
                                                                        #Что бы сайты думали что - рельный пользователь.
  #.add_argument('--headless') #режим работы в фоне
  # указать путь к драйверу браузера и опции, при необходимости добавить прокси
  driver = webdriver.Chrome(executable_path=r"C:\Users\Алексей\PycharmProjects\parser_anagram\chromedriver.exe",
                            options=options)
  driver.maximize_window()  # Размер окна на максимум

  try:
    # driver.refresh() #перезагрузка страницы
    # driver.get_screenshot_as_file("1.png") #сделать скрин
    driver.get(nv)

    #########  скрол до низа страницы и обратно для корректной прогрузки товаров
    scroll_page(driver)
    time.sleep(3)  # пауза
    # Ищем товары на стрнарице по классу
    product = driver.find_elements("class name", 'modal-card__description')

    #Перебираем найденные товары
    i = 0
    while i < len(product) - 1:
      element = product[i]
      time.sleep(1)  # пауза
      # т.к. class - modal-card__description находится внутри другого html тега, нужно обратиться именно к нему.
      # Иначе клик будет попадать на внешний объект
      driver.execute_script("arguments[0].scrollIntoView();", element)
      driver.execute_script("arguments[0].click();", element)

      #сохраняем файл с нашей страницей после клика по товару
      with open("index_selenium.html", "w", encoding="utf-8") as file:
        file.write(driver.page_source)

      #открываем файл и записываем в переменную. Пока оставим такую конструкцию
      with open("index_selenium.html") as file:
        src = file.read()

      soup = bs4.BeautifulSoup(src, features='html.parser') #пребразуем в элемент Bs4
      name = soup.find_all('h5', class_ = "modal-card__headline") #Находим название товара
      img_obg = soup.find('img', class_="mfp-img")  # Находим название товара
      tm = soup.find_all('p', class_="modal-card__description headline") #находим значение торговой марки
      pr = soup.find('div', class_="modal-card__info") #получаем объект в котором находятся характеристики
      pr1 = pr.find_all('p', class_="modal-card__description") #Ищем о объекте характеристики

      name = name[0].text
      tm = tm[0].text
      img = img_obg.get('src')

      #Через функцию находим есть ли характеристика у товара. Если есть то получим ее индекс, если нет, то получим -1
      index = find_pr(pr1, 'Helium')
      if index != -1:
        helium = pr1[index].text
      else:
        helium = '-'

      index = find_pr(pr1, 'Minimum')
      if index != -1:
        mwr = pr1[index].text
      else:
        mwr = '-'

      index = find_pr(pr1, 'Maximum')
      if index != -1:
        max = pr1[index].text
      else:
        max = '-'

      index = find_pr(pr1, 'Inflated')
      if index != -1:
        inflated = pr1[index].text
      else:
        inflated = '-'

      #запись в df
      add_in_df_usa(df,name, tm, helium, mwr, max, inflated, img)

      #нажимаем закрыть чтобы закрыть модальное окно товара
      webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
      i += 1

    time.sleep(15)

  except Exception as ex:
    print(ex)
  finally:
    driver.close()
    driver.quit()

#фнкция собирает все ссылки на товары
def get_pr_list(pr_list,nv):
  print('Сбор ссылок на товары, страница: ', nv,)

  response = requests.get(nv, cookies=cookies, headers=headers)  # Запрос к первой странице
  soup = bs4.BeautifulSoup(response.text, features='html.parser')  # преобразуем
  products = soup.find_all('a', class_="goods_name")  # ищем товары
  print('Найдено товаров: ', int(len(products)/2))
  #Добавляем в список ссылки на все товары
  i = 0
  while i < len(products):
    pr_list.append('https://sharik.ru' + products[i].get('href'))
    i += 2

  return pr_list #Список для ссылок на товары

#функция вытасиквае данные параметры товаров
def parse_product(df_rus,pr_list):
  #выполняем запрос к каждому товару
  j = 0
  for pr in pr_list:
    response = requests.get(pr, cookies=cookies, headers=headers)  # Запрос к первой странице
    soup = bs4.BeautifulSoup(response.text, features='html.parser')  # преобразуем
    name = soup.find('h1', itemprop="name")
    art = soup.find('span', class_="H1")
    parametrs = soup.find('td', style="padding: 14px 30px 0px 24px; text-align:left; vertical-align: top; width:100%")
    parametrs = parametrs.find_all('td', class_="tablebody")

    #ищем порядковый номер поля Штрих код, он может быть разный, Если он есть за ним +1 всегда сам код
    index = find_pr(parametrs, 'Штрих')
    if index != -1:
      code = parametrs[index + 1].text
    else:
      code = '-'

    add_in_df_rus(df_rus, name, art, code, j)
    j += 1



def parse_usa():
  url = 'https://anagramballoons.com'  # сайт
  nav = '?page='  # способ навигации по станицам
  df = pd.DataFrame([], columns= ['Код', 'Товар',
                                  'Helium Volume',
                                  'Minimum Weight Requirement',
                                  'Maximum Elevation',
                                  'Inflated Size',
                                  'TM',
                                  'img'])

  # ссылки на категории которые будем парсить
  list_category = ['https://anagramballoons.com/products/specialty-format/',
                   'https://anagramballoons.com/products/ultrashapes/',
                   'https://anagramballoons.com/products/supershape/',
                   'https://anagramballoons.com/products/airwalkers/']

  print("Парсинг сайта: ", url)
  # Проверяем доступность сайта
  con = connect(url)
  if con == 200:
    print(url, 'Страница, доступна, код:', con, '\n')
    #перебираем список с разделами list_category
    for category in list_category:
      print('Поиск уникальных страниц в разделе: ', category)
      nav_list = get_page_list(category, nav, 1)
      if nav_list != 400: #вернет 400 если нет ни одного товара на странице
        #перебираем список уникальных страниц в разделе
        for nv in nav_list:
          open_category(df,nv)
    print(url, 'Сбор данных закончен, файлы сохранены')
  else:
    print(url, 'Страница не доступна, код', con,)
    exit()

def parse_rus():
  url = 'https://sharik.ru/production/prod/list_prmsection_id_dta857.html'
  nav = '?PAGEN_100='
  pr_list = []  # Список для ссылок на товары
  df_rus = pd.DataFrame([], columns=['Артикул рус.',
                                     'Название',
                                     'Штрих-код',
                                     'Код','*'])

  print("Парсинг сайта: ", url)
  # Проверяем доступность сайта
  con = connect(url)
  if con == 200:
    print(url, 'Страница, доступна, код:', con, '\n')
    # получаем список уникальных страниц
    nav_list = get_page_list(url, nav, 2)
    if nav_list != 400: #вернет 400 если нет ни одного товара на странице
      for nv in nav_list:
        get_pr_list(pr_list, nv)

    parse_product(df_rus, pr_list)
    print(url, 'Сбор данных закончен, файлы сохранены')



  else:
    print(url, 'Страница не доступна, код', con,)
    exit()


def unite(df1,df2):
  df1['Код'] = df1['Код'].astype(str)
  df2['Код'] = df2['Код'].astype(str)

  df3 = df1.merge(df2, how='inner', on='Код',)
  df3.to_csv(r'parse_result_inner.csv')

  #df3 = df1.merge(df2, how='outer', on='Код', )
  #df3.to_csv(r'parse_result_outer.csv')
  print('\n созданы объединённые файлы')

def metrics(df1,df2,df3):
  #Найдём больший датасет
  if len(df1.index) > len(df2.index):
    big = len(df1.index)
    small = len(df2.index)
  else:
    big = len(df2.index)
    small = len(df1.index)

  proportions = big/small
  rel = big/len(df3.index)
  print('Обе метрики должны стремиться к 1')
  print('Пропорциональность: ',proportions, 'отношение: ', rel)

def main():
  parse_rus()
  parse_usa()

  df1 = pd.read_csv(r'C:\Users\Алексей\PycharmProjects\parser_anagram\parse_usa.csv')
  df2 = pd.read_csv(r'C:\Users\Алексей\PycharmProjects\parser_anagram\parse_rus.csv')
  unite(df1, df2)

  df3 = pd.read_csv(r'C:\Users\Алексей\PycharmProjects\parser_anagram\parse_result_inner.csv')
  metrics(df1, df2, df3)


main()





