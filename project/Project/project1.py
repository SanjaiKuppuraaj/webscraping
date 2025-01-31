from xml.sax.handler import property_dom_node

import requests
from bs4 import BeautifulSoup as bs

urls = 'https://www.amazon.in/s?k=headphones&ref=nb_sb_noss'
headers = {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36','cookie':'session-id=257-1941260-5956767; session-id-time=2082787201l; i18n-prefs=INR; ubid-acbin=258-6923941-9670512; session-token=sL0Z8eUR7y46RjAHbGGDiLRVBcfnbsf6nz09dABJInsDFn7P95qM3s/MbIZuM6/ZKAM7g0Z6Sfb78kk3kboRlpdV/7ZXDCDtc0kziL8xyvxl/fAGLjm4FGV0ZBA48saU5Xn7oGgh/ZDhAd8soTpJgUdifoPpi4duY5CaoQa2J4XoqF+a8jjaAdSfFpJYi6DXUr0WD+oNrEPo/aax05Thi6VEbvPStZtdLeu+N4b54PdzvmaEubkhZ4mmNCBaQZ6LOgrhqZxP680e/Whd720hMVYNsKZKXnS1G0XwTMENn2Vy5zd+6TK6B8ONIPo+B7X9RmyZ7uHrjChw92mjxog0B1NSP8PoV2G4; csm-hit=tb:2YR6DWSK3VK6BKKAZX9N+s-MMFJXMAG8KMM99AF22BN|1734530366843&t:1734530366843&adb:adblk_no',
           'viewport-width':'725'}
response = requests.get(urls,headers=headers)
soups = bs(response.text,'html.parser')
datas = soups.find_all('div',{'class':'puis-card-container'})
for k in datas:
    sol_data = dict()
    sol_data['Product_name'] = k.find('h2',{'class':'a-size-medium a-spacing-none a-color-base a-text-normal'}).text
    sol_data['Price'] = k.find('span',{'class':'a-price'}).find('span').text.strip('₹')
    sol_data['Product_link'] = 'https://www.amazon.in' + (k.find('a')['href'])
    print(sol_data)

