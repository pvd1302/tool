import copy
import os
import uuid
import re
import time
from dotenv import load_dotenv

import requests
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPBasicAuth
from selenium import webdriver

from bs4 import BeautifulSoup as bs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

import pdfkit
import shutil

# -*- coding: utf-8 -*-
load_dotenv('config.env')

session = requests.Session()
reties = Retry(total=3,
               backoff_factor=0.1,
               status_forcelist=[500, 502, 503, 504, 400, 401, 404])

session.mount("http://", requests.adapters.HTTPAdapter(max_retries=reties))
session.mount("https://", requests.adapters.HTTPAdapter(max_retries=reties))


def downloadFile(link, file_name):
    path_download = "download"
    os.makedirs(path_download, exist_ok=True)
    basic = HTTPBasicAuth('mobio', 'mobio!@#456')
    resp = session.get(link, auth=basic)
    r = os.path.join(path_download, file_name)

    with open(r, 'w', encoding="UTF-8") as f:
        resp_text = resp.text
        resp_text = resp_text.replace("border: 1px solid var(--main-gray);", "border: 1px solid #000;")
        f.write(resp_text)
    return r


def replace_link_css_or_image(link):
    link = link.replace('assets', domain + '/assets')
    link = link.replace('vendor', domain + '/vendor')
    link = link.replace('css/', domain + '/css/')
    link = link.replace('img/', domain + '/img/')
    return link

def convert_filename(filename):
    new_filename = copy.deepcopy(filename)
    if "?v=" in new_filename:
        new_filename = new_filename.split("?v=")[0]
    _, file_ext = os.path.splitext(new_filename)
    new_file_name = str(uuid.uuid1()) + file_ext
    return new_file_name


if __name__ == '__main__':
    username = "mobio"
    password = "mobio!@#456"
    replace_pass = {'!': '%21',
                    '"': '%22',
                    '#': '%23',
                    '$': '%24',
                    '&': "%26",
                    "'": '%27',
                    '(': '%28',
                    ')': '%29',
                    '*': '%2A',
                    '+': '%2B',
                    ',': '%2C',
                    '-': '%2D',
                    '.': '%2E',
                    '/': '%2F',
                    ':': '%3A',
                    '<': '%3C',
                    '=': '%3D',
                    '>': '%3E',
                    '?': '%3F',
                    '@': '%40'}
    for key, value in replace_pass.items():
        password = password.replace(key, value)
    PATH_WKHTMLTOPDF = os.getenv('PATH_WKHTMLTOPDF')
    path_wkhtmltopdf = r'{}'.format(PATH_WKHTMLTOPDF)
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    FILE_LINK_EXPORT = os.getenv('FILE_LINK_EXPORT')

    repos = []
    with open(FILE_LINK_EXPORT) as infile:
        for line in infile:
            line = line.strip()
            if line:
                repos.append(line)
    for url in repos:
        print(url)
        nameDelete = url.split('#api-')
        first = ''
        apiName = url.split('/#')
        divIDApiName = apiName[1]
        domain = apiName[0]
        split_url = url.split('https://')
        parse_url = "https://" + username + ":" + password + "@" + split_url[1]
        edge_options = webdriver.ChromeOptions()
        edge_options.add_argument("--headless")
        driver = webdriver.Chrome(edge_options)
        driver.get(parse_url)
        html = driver.page_source

        timeout = 100
        count = 3
        body = None
        while count > 0:
            print("Start find :: ", count)
            element_present = EC.presence_of_element_located((By.ID, apiName[1]))
            WebDriverWait(driver, timeout).until(element_present)
            html = driver.page_source

            soup = bs(html, 'html.parser')
            header_example = soup.find_all("a", href=re.compile("#header-examples-" + nameDelete[1]))
            a_error_example = soup.find_all("a", href=re.compile("#error-examples-" + nameDelete[1]))
            div_error_example = soup.find_all("div", id=lambda id: id and "error-examples" in id)

            if header_example and len(header_example) > 1:
                header_example.pop(0)
            for e in header_example:
                e.extract()
            for e3 in a_error_example:
                e3.extract()
            for e4 in div_error_example:
                e4.extract()
            body = soup.find('div', {'id': divIDApiName})
            if body:
                break
            count -= 1
        #
        print("Start download link css/image")

        for a in soup.find_all('link'):
            a_href = a['href']
            a_href = replace_link_css_or_image(a_href)
            if a_href.startswith(domain):
                file_new = a_href.replace(domain, "")
                a_href = downloadFile(a_href, convert_filename(file_new))
            a['href'] = a_href
        print("Start convert to html")
        head = soup.find('head')

        result = str(head) + str(body)

        outFilePathHtml = divIDApiName + ".html"
        outFilePathPdf = divIDApiName + ".pdf"
        print("Start save file html")
        with open(outFilePathHtml, "w", encoding="UTF-8") as f:
            f.write(result)
        #
        print("Start config export file pdf")
        try:
            pdfkit.from_file(outFilePathHtml, outFilePathPdf, options={"enable-local-file-access": ""},
                             configuration=config)
        except:
            print("Export done")
        os.remove(outFilePathHtml)
    shutil.rmtree("download")
