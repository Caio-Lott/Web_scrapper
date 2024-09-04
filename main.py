import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

class DataScraper:
    def __init__(self, url):
        self.url = url
        self.driver = self._initialize_driver()
        self.soup = None

    def _initialize_driver(self):
        options = Options()
        options.add_argument("--headless") 
        driver = webdriver.Chrome(options=options)
        return driver

    def fetch_page(self):
        self.driver.get(self.url)
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'h2.ng-binding'))
        )
        self.soup = BeautifulSoup(self.driver.page_source, 'html.parser')

    def find_top_rankings(self, h2_text):
        if not self.soup:
            raise ValueError("A página não foi carregada. Chame fetch_page() primeiro.")
        
        # Encontrar o <h2> com o texto especificado
        h2 = self.soup.find('h2', class_='ng-binding', string=h2_text)
        if h2:
            # Encontrar o div pai do <h2>
            parent_div = h2.find_parent('div')
            if parent_div:
                # Encontrar os três primeiros <li> dentro do div pai
                list_items = parent_div.find_all('li', limit=3)
                rankings = []
                for item in list_items:
                    company_name = item.get_text(strip=True)
                    link = item.find('a', href=True)
                    if link:
                        rankings.append((company_name, link['href']))
                return rankings
        return []

    def clean_company_names(self, rankings):
        # Função para limpar o nome da empresa removendo números e outros textos
        cleaned_names = []
        for name, link in rankings:
            # Remove números e o texto "ver mais informações"
            clean_name = re.sub(r'\d+.*', '', name).strip()
            cleaned_names.append((clean_name, link))
        return cleaned_names

    def fetch_company_value(self, company_link):
        try:
            # Verifique se o link já contém o domínio base
            if not company_link.startswith('http'):
                company_link = f"https://www.reclameaqui.com.br{company_link}"
            
            self.driver.get(company_link)
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'b.go3621686408'))
            )
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            b_tags = soup.find_all('b', class_='go3621686408')
            if b_tags:
                values = [b.get_text(strip=True) for b in b_tags]
                return values if values else "Valor não encontrado"
            return "Valor não encontrado"
        except Exception as e:
            print(f"Erro ao acessar o link {company_link}: {e}")
            return "Erro ao acessar"

    def save_to_csv(self, data, filename):
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Nome da empresa', 'Categoria', 'Nota', 'Link'])
            for entry in data:
                writer.writerow(entry)

    def close(self):
        self.driver.quit()

url = 'https://www.reclameaqui.com.br/ranking/'
scraper = DataScraper(url)
scraper.fetch_page()

# Coletar e limpar dados das melhores empresas dos últimos 30 dias
rankings_melhores_30_dias = scraper.find_top_rankings('Melhores empresas que mais resolveram nos últimos 30 dias')
cleaned_names_melhores_30_dias = scraper.clean_company_names(rankings_melhores_30_dias)

# Coletar e limpar dados das piores empresas dos últimos 30 dias
rankings_piores_30_dias = scraper.find_top_rankings('Piores empresas nos últimos 30 dias')
cleaned_names_piores_30_dias = scraper.clean_company_names(rankings_piores_30_dias)

# Obter o valor do <b> com a classe go3621686408 para cada empresa e preparar dados para Excel
data = []
for name, link in cleaned_names_melhores_30_dias:
    full_link = f"https://www.reclameaqui.com.br{link}" if not link.startswith('http') else link
    print(f"Acessando URL: {full_link}")
    values = scraper.fetch_company_value(full_link)
    if isinstance(values, list):
        for value in values:
            data.append([name, 'Melhores', value, full_link])
    else:
        data.append([name, 'Melhores', values, full_link])

for name, link in cleaned_names_piores_30_dias:
    full_link = f"https://www.reclameaqui.com.br{link}" if not link.startswith('http') else link
    print(f"Acessando URL: {full_link}")
    values = scraper.fetch_company_value(full_link)
    if isinstance(values, list):
        for value in values:
            data.append([name, 'Piores', value, full_link])
    else:
        data.append([name, 'Piores', values, full_link])

df = pd.DataFrame(data)
df.to_excel("ranking_empresas.xlsx")

scraper.close()
