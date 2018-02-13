import time
import requests
from bs4 import BeautifulSoup
import urllib.parse
import base64
import hashlib

url_argo = "" # link al vostro registro (esempio http://www.codicescuola.scuolanext.info/)
codice_scuola = "" # codice scuola
username = "" # nome utente registro elettronico dello studente
password = "" # password registro elettronico dello studente

github = True # abilita la pubblicazione su github, da disabilitare per modifiche future
username_github = "" # nome utente di github
repository = "" # nome del repository usato da github pages
auth_token = "" # auth token di github (generabile qui https://github.com/settings/tokens)

# creo una sessione allo scopo di mantentenere i cookie tra le varie richieste
session = requests.Session()
session.get(url_argo)

# eseguo il login
payload = {
    'j_password': password,
    'j_username': username + "#" + codice_scuola,
    'submit' : 'Entra',
    'utente' :  username,
}
session.post("https://www.portaleargo.it/argoweb/famiglia/common/j_security_check", data=payload)

# ottemgo i compiti
payload = {
    'BackbaseClientDelta' :'[evt=menu-serviziclasse:_idJsp25|event|submit][att=_idJsp24|selected|true][att=_idJsp5|selected|false]'
}
risposta_compiti = session.post("https://www.portaleargo.it/argoweb/famiglia/index.jsf", data=payload)
html_compiti = risposta_compiti.text

#interpreto l'html
soup =  BeautifulSoup(html_compiti, 'html.parser')
giorni_compiti = soup.select('.fieldset-anagrafe')

html_pagina = ""

#inizio a creare l'html
html_pagina = html_pagina + '''
<html>
  <head>
    <meta charset="utf-8"/>
    <title>Compiti Classe 2A</title>

    <style>
        ul {
            list-style: none;
        }

        .compiti li {
            margin-bottom: 40px;
        }

        p {
            margin: 7px;
        }

        .giorno {
            font-weight: bold;
            font-size: 15pt;
        }

        .aggiornamento {
            font-weight: bold;
            font-size: 15pt;
        }
    </style>
  </head>
  <body>
'''

# metto la data dell'ultimo aggiornamento della pagina
oggi = time.strftime("%d/%m/%Y %H:%M:%S")
html_pagina = html_pagina + '<p class="aggiornamento">ultimo aggiornamento : ' + oggi + '</p>'

# inizio a creare la lista dei compiti
html_pagina = html_pagina + '<ul class="compiti">'

# scorro i giorni
for compiti_giorno in giorni_compiti:
    html_pagina = html_pagina + '<li>'

    # scrivo il giorno
    data = compiti_giorno.select('legend')
    giorno = data[0].text
    html_pagina = html_pagina + '<p class="giorno">' + giorno + '</p>'

    #scorro le materie di ogni giorno
    materia_compito = compiti_giorno.select('tr')
    for materia in materia_compito:
        materie = materia.select('b')
        #fix bug registro che mette giorni vuoti
        if len(materie) == 0:
            continue

        # scrivo la materia del compito
        nome_materia = materie[0].text
        html_pagina = html_pagina + '<p>' + nome_materia + '</p>'

        # scrivo il compito
        compito = materia.select('td')[1]
        indicazioni_compito = compito.text
        html_pagina = html_pagina + '<p>' + indicazioni_compito + '</p>'

    html_pagina = html_pagina + '</li>'

# chiudo il file html
html_pagina = html_pagina + '''
        </ul>
    </body>
</html>
'''

#creo il file "compiti"(non serve per il funzionamento del programma, ma serve per testare in locale)
with open("compiti.html", "w") as f:
    f.write(html_pagina)

# abilito github
if github:
    HEADER_GITHUB = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": "token " + auth_token,
    }

    # chiediamo a github qual'è stato l'ultimo commit
    url = 'https://api.github.com/repos/'+ username_github + '/' + repository + '/git/refs/heads/master'
    r = requests.get(url, headers=HEADER_GITHUB)

    print(r.text)

    # otteniamo lo sha dell'ultimo commit
    # lo sha è un identificativo univoco di un commit
    last_commit_sha = r.json()['object']['sha']
    last_commit_url = r.json()['object']['url']

    # otteniamo il tree
    r = requests.get(last_commit_url, headers=HEADER_GITHUB)

    print(r.text)

    tree_sha = r.json()['tree']['sha']
    tree_url = r.json()['tree']['url']

    # carichiamo il file modificato (index.html)
    base64_html = base64.b64encode(html_pagina.encode('utf-8')).decode('utf-8')

    url = 'https://api.github.com/repos/'+ username_github + '/' + repository + '/git/blobs'
    r = requests.post(url, json={
        "content": str(base64_html),
        "encoding": "base64",
    }, headers=HEADER_GITHUB)

    print(r.text)

    blob_sha = r.json()['sha']

    # aggiorniamo il file index.html, caricato nella richiesta precedente
    url = 'https://api.github.com/repos/'+ username_github + '/' + repository + '/git/trees'
    r = requests.post(url, json={
        "base_tree": tree_sha,
        "tree": [
            {
                "path": "index.html",
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha,
            }
        ],
    }, headers=HEADER_GITHUB)

    print(r.text)

    new_tree_sha = r.json()['sha']

    # Creiamo il commit
    url = 'https://api.github.com/repos/'+ username_github + '/' + repository + '/git/commits'
    r = requests.post(url, json={
        "message": "Aggiorna Compiti",
        "tree": new_tree_sha,
        "parents": [
            last_commit_sha,
        ],
    }, headers=HEADER_GITHUB)

    print(r.text)

    new_commit_sha = r.json()['sha']

    # "Pubblichiamo" il commit
    url = 'https://api.github.com/repos/'+ username_github + '/' + repository + '/git/refs/heads/master'
    r = requests.patch(url, json={
        "sha": new_commit_sha,
    }, headers=HEADER_GITHUB)

    print(r.text)
