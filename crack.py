import cv2
import numpy as np

import time
from bs4 import BeautifulSoup
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import csv
import os
import re
import locale
from datetime import datetime
from pathlib import Path
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

def locate_captcha(element):
    left = element.location['x']
    right = element.location['x'] + element.size['width']
    top = element.location['y']
    bottom = element.location['y'] + element.size['height']
    #print('left: ', left, 'right: ', right, 'top: ', top, 'bottom: ', bottom)
    return left, top, right, bottom

def save_captcha(fname, location):
    img = Image.open(fname)
    img = img.crop(location)
    #img.show()
    img.save(str(Path('data', 'captcha')) + '.png')

def recong_captcha(fname):
    img = cv2.imread(fname)
    
    kernel = np.ones((4, 4), np.uint8)
    erosion = cv2.erode(img, kernel, iterations=1)
    blurred = cv2.GaussianBlur(erosion, (5, 5), 0)
    edged = cv2.Canny(blurred, 30, 150)
    dilation = cv2.dilate(edged, kernel, iterations=1)

    #找出輪廓
    contours, hierarchy = cv2.findContours(dilation.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted([(c, cv2.boundingRect(c)[0]) for c in contours], key = lambda x: x[1])

    char_array = []
    for (c, _) in cnts:
        (x, y, w, h) = cv2.boundingRect(c)
        if w > 13 and h > 13:
            char_array.append((x, y, w, h))
    
    #fig = plt.figure()
    for i, (x, y, w, h) in enumerate(char_array):
        roi = dilation[y:y+h, x:x+w]
        thresh = roi.copy()
        #a = fig.add_subplot(1, len(char_array), i+1)
        res = cv2.resize(thresh, (50, 50))
        cv2.imwrite(str(Path('data', '{}'.format(i))) + '.png', res)
        #plt.imshow(res)
    #plt.show()

    alphabets = ''
    for i in range(5):
        img = cv2.imread(str(Path('data', '{}'.format(i))) + '.png')
        alphabet, _ = getAlphabet(img)
        alphabets = alphabets + alphabet
    return alphabets

def mse(img1, img2):
    err = np.sum((img1.astype('float') - img2.astype('float')) ** 2) 
    err /= float(img1.shape[0] * img1.shape[1])
    return err

def getAlphabet(img):
    min_a = 9999999999
    min_png = None
    for png in os.listdir('alphabet'):
        ref = cv2.imread('alphabet' + os.path.sep + png)
        if mse(ref, img) < min_a:
            min_a = mse(ref, img)
            min_png = png
    alphabet = min_png.split('.')[0]
    return alphabet, min_a
    
def find_unchinese(file):
    #pattern = re.compile(r'[\u4E00-\u9FA5]|\u3000')
    pattern = re.compile(r'[\u4E00-\u9FA5]|[\u25A0-\u25FF]|[\u2B00-\u2BFF]|[\u2500-\u259F]|\u3000|\u0020')
    unchinese = re.sub(pattern, "", file)
    return unchinese

def read_stock_code(file_path):
    assert type(file_path) == str
    stock_codes = []
    
    with open(file_path, 'r') as file_r:
        csv_r = csv.reader(file_r)

        #skip the header
        header = next(csv_r)

        for i, r in enumerate(csv_r):
            if r != []:
                stock_codes.append(r[0])
    return stock_codes

def scrape_web(stock_codes):
    screenshot_path = str(Path('data', 'page1.png'))
    options = Options()
    options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    driver_item = webdriver.Chrome(chrome_options=options, executable_path="/Users/sunyenpeng/Desktop/python/cooperation/chromedriver_mac_arm64 (2)/chromedriver")
    driver_item.set_window_position(0, 0)
    driver_item.set_window_size(1080, 720) #1960,1080

    idx = 0
    while idx != len(stock_codes):

        code = stock_codes[idx]

        driver_item.get('https://bsr.twse.com.tw/bshtm/')

        driver_item.switch_to.frame('page1')

        driver_item.find_element_by_id('TextBox_Stkno').click()
        driver_item.find_element_by_id('TextBox_Stkno').clear()
        driver_item.find_element_by_id('TextBox_Stkno').send_keys(code)
        driver_item.find_element_by_id('form1').submit()

        driver_item.save_screenshot(screenshot_path)

        img_e = driver_item.find_element_by_xpath(
            '//html/body/form/div[3]/table/tbody/tr[2]/td/table/tbody/tr[3]/td/div/table/tbody/tr/td/table/tbody/tr[1]/td/div/div[1]/img')
        location = locate_captcha(img_e)
        save_captcha(screenshot_path, location)
        captcha_t = recong_captcha(str(Path('data', 'captcha')) + '.png')
        #print(captcha_t)
        captcha_e = driver_item.find_element_by_xpath(
            '/html/body/form/div[3]/table/tbody/tr[2]/td/table/tbody/tr[3]/td/div/table/tbody/tr/td/table/tbody/tr[1]/td/div/div[1]/img')
        captcha_e.click()
        captcha_e.clear()
        captcha_e.send_keys(captcha_t)

        driver_item.find_element_by_id('btnOK').click()

        driver_item.switch_to.default_content()
        driver_item.switch_to.frame('page2')

        driver_item.get('https://bsr.twse.com.tw/bshtm/bsContent.aspx?v=t')
        try:
            element = WebDriverWait(driver_item, 10).until(
                EC.presence_of_element_located((By.ID, "table2"))
            )
        except TimeoutException:
            print('Verification Fail!')
            continue
        soup = BeautifulSoup(driver_item.page_source, 'html.parser')
        tables = soup.find_all('table', id='table2')

        filename = str(code) + '_update.csv'
        file_out = Path('data', 'download', filename)
        file_out.touch()

        header = ['No.', 'Stock Seller', 'Deal price', 'Buy in', 'Sold out']
        # https://zh.codeprj.com/blog/9ebeb41.html
        # https://www.cnblogs.com/adampei-bobo/p/8615978.html
        with file_out.open('w', encoding='utf-8-sig', newline='') as csv_out:
            csv_w = csv.writer(csv_out)
            csv_w.writerow(header)

            for table in tables:
                body = table.find('tbody').find('tr')
                rows = body.find_all('tr')

                record = {}
                for row in rows:
                    # https://www.learncodewithmike.com/2020/05/python-selenium-scraper.html
                    # https://stackoverflow.com/questions/7003832/checking-for-attributes-in-beautifulsoup
                    try:
                        #print(row['class'])
                        if row['class'][0] == 'column_value_price_2' or row['class'][0] == 'column_value_price_3':
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            if cols[0] != '':
                                cols[1] = find_unchinese(cols[1])
                                cols[2] = locale.atof(cols[2])
                                cols[3] = locale.atof(cols[3])
                                cols[4] = locale.atof(cols[4])
                                record[int(cols[0])] = cols
                                #count = count + 1
                    except KeyError:
                        continue
                # https://careerkarma.com/blog/python-sort-a-dictionary-by-value/
                record_sorted = sorted(record.items(), key=lambda x: x[0])

                # https://www.delftstack.com/zh-tw/howto/python/write-list-to-csv-python/
                for r in record_sorted:
                    csv_w.writerow(r[1])
        time.sleep(10)
        idx += 1
    driver_item.close()
    driver_item.quit()

if __name__ == '__main__':
    filename = "stock.csv"
    now = datetime.now().strftime("%Y_%m_%d")
    filename = now + '_' + filename
    stock_csv = str(Path('data', filename))

    stock_codes = read_stock_code(stock_csv)
    scrape_web(stock_codes)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
