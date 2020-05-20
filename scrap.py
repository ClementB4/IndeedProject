import requests as rq
from bs4 import BeautifulSoup as bs
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')
db=client.indeed


metiers = ['développeur', 'data scientist', 'data analyst', 'business intelligence']
localisations = ['Paris', 'Lyon', 'Toulouse', 'Nantes', 'Bordeau', 'Nancy']
contrats = ['permanent', 'contract', 'temporary', 'custom_1', 'apprenticeship', 'internship', 'subcontract', 'fulltime', 'parttime']

# metiers = ['developpeur']
# localisations = ['Paris']
# contrats = ['permanent']

# def ask(metier='', localisation='', contrat=''):
#     if len(metier) > 0:
#          localisation = input('Veuillez réécrire votre localisation : ')
#     else:
#         metier = input('Quel est le métier de votre recherche ? ')
#         localisation = input('Quel est la ville ou la région de votre recherche ?')
#         contrat_o_n = input('Voulez vous rentrer un type de contrat précis ? o/n : ').lower()
#         while contrat_o_n not in ['o', 'n']:
#             print("Pas compris")
#             contrat_o_n = input('Voulez vous rentrer un type de contrat précis ? o/n : ').lower()
#         if contrat_o_n == 'o':
#             contrat = input('Quel est votre type de contrat ?  \n CDI = 1; CDD = 2; Intérim = 3; Contrat pro = 4; Apprentissage = 5; Stage = 6; Freelance/Indépendant = 7; Temps plein = 8; Temps partiel = 9\n')
#             contrat_type = {'1':'permanent', '2':'contract', '3':'temporary', '4':'custom_1', '5':'apprenticeship', '6':'internship', '7':'subcontract', '8':'fulltime', '9':'parttime'}
#             contrat = contrat_type[contrat]    
#         else:
#             pass
#     return metier, localisation, contrat

def verification(metier, localisation, contrat):
    if len(contrat) > 0:
        page = rq.get(f"https://www.indeed.fr/emplois?q={metier}&l={localisation}&jt={contrat}")
    else:
        page = rq.get(f"https://www.indeed.fr/emplois?q={metier}&l={localisation}")
    soup = bs(page.content, 'html.parser')
    td = soup.find('td', id='resultsCol')
    while len(td.find_all('div', {'class':'invalid_location'})) > 0 or len(td.find_all('div', {'class':'no_results'})) > 0:
        if len(td.find_all('div', {'class':'invalid_location'})) > 0:
            print("La localisation demandé n'a pas pu être trouvé probablement dû à une faute d'orthographe. \nVeuillez rééssayer.")
            metier, localisation, contrat = ask(metier=metier, contrat=contrat)
        elif len(td.find_all('div', {'class':'no_results'})) > 0:
            print(f"Aucun emploi correspondant à la recherche : {metier} à {localisation} avec votre type de contrat, veuillez recommencer.")
            metier, localisation, contrat = ask()
        page = rq.get(f"https://www.indeed.fr/emplois?q={metier}&l={localisation}&jt={contrat}")
        soup = bs(page.content, 'html.parser')
        td = soup.find('td', id='resultsCol')
    else:
        print('Vérification valide.')
    return soup

def id_exist(id_test):
    return db['data'].count_documents({'_id':id_test}) > 0

def id_link_title(soup, job):
    td = soup.find('td', id='resultsCol')
    for a in td.find_all('a', rel='noopener nofollow'):
        if id_exist(a['id']):
            print('Id déjà existente.')
        else:
            job['id'].append(a['id'])
            job['lien'].append('http://www.indeed.fr/{}'.format(a['href']))
            job['poste'].append(a.get_text()[1:])
    
def get_company(soup, job):
    span = soup.find_all('span', {'class':'company'})
    for x in span:
        job['entreprise'].append(x.get_text()[1:])

def get_adress(soup, job):
    span = soup.find_all('span', {'class':'location accessible-contrast-color-location'})
    div = soup.find_all('div', {'class':'location accessible-contrast-color-location'})
    for x in span:
        job['lieu'].append(x.get_text())
    for x in div:
        job['lieu'].append(x.get_text())

def with_links(links, job):
    for link in links:
        page = rq.get(link)
        soup_temp = bs(page.content, 'html.parser')
        for div in soup_temp.find_all('div', {'class':'jobsearch-JobMetadataFooter'}):
            for child in div.find_all('div'):
                child.decompose()
            job['publication'].append(div.get_text().split(' - ')[1])
        for div in soup_temp.find_all('div', {'id':'jobDescriptionText'}):
            job['description'].append(div.get_text())
        if soup_temp.find_all('div', {'class':'icl-IconFunctional icl-IconFunctional--jobs icl-IconFunctional--md'}) == []:
            job['contrat'].append('')
        else:
            for icone in soup_temp.find_all('div', {'class':['icl-IconFunctional icl-IconFunctional--jobs icl-IconFunctional--md']}):
                job['contrat'].append(icone.find_parent('div').get_text())
        if soup_temp.find_all('div', {'class':'icl-IconFunctional icl-IconFunctional--salary icl-IconFunctional--md'}) == []:
            job['salaire'].append('')
        else:
             for icone in soup_temp.find_all('div', {'class':'icl-IconFunctional icl-IconFunctional--salary icl-IconFunctional--md'}):
                job['salaire'].append(icone.find_parent('div').get_text())

def get_next_page(soup):
    a = soup.find_all('a', {'aria-label':'Suivant'})
    for x in a:
        next_link = 'http://www.indeed.fr/{}'.format(x['href'])
        next_page = rq.get(next_link)
        next_soup = bs(next_page.content, 'html.parser')
    return next_soup

def suivant(soup):
    if soup.find_all('a', {'aria-label':'Suivant'}) == []:
        print('Pas de page suivante.')
    elif soup.find_all('b', {'aria-current':'true', 'aria-label':'15'}) != []:
        print('Dernière page.')
    else:
        print('Page suivante.')
        job = reset_job()
        next_soup = get_next_page(soup)
        id_link_title(next_soup, job)
        get_company(next_soup, job)
        get_adress(next_soup, job)
        with_links(job['lien'], job)
        suivant(next_soup)
              
def add_db(job):
    for i in range(len(list(job.values())[0])):
        to_add = {
            '_id':job.get('id')[i],
            'lien':job.get('lien')[i],
            'poste':job.get('poste')[i],
            'entreprise':job.get('entreprise')[i],
            'contrat':job.get('contrat')[i],
            'lieu':job.get('lieu')[i],
            'salaire':job.get('salaire')[i],
            'publication':job.get('publication')[i],
            'description':job.get('description')[i]
        }
        db['data'].insert_one(to_add)

def reset_job():
    job = {
        'id':[], 'lien':[], 'poste':[], 
        'entreprise':[], 'contrat':[], 'lieu':[], 
        'salaire':[], 'publication':[], 'description':[]
        }
    return job

def run():
    for metier in metiers:
        for localisation in localisations:
            for contrat in contrats:
                job = reset_job()
                soup = verification(metier, localisation, contrat)
                id_link_title(soup, job)
                get_company(soup, job)
                get_adress(soup, job)
                with_links(job['lien'], job)
                suivant(soup)
                add_db(job)
            print('Fin contrat pour %s à %s'%(metier, localisation))
        print('Fin localisation pour %s'%(metier))
    print('Fin. Youpi')
    
run()

client.close()