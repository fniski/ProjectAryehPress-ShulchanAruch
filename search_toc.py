import requests

def search(nodes):
    for n in nodes:
        if 'title' in n and 'Zahav' in n['title']:
            print(n['title'])
        if 'contents' in n:
            search(n['contents'])

r = requests.get('https://www.sefaria.org/api/index').json()
search(r)
