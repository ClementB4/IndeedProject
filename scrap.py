import requests as rq
from bs4 import BeautifulSoup as bs
from pymongo import MongoClient
import time

client = MongoClient('mongodb://localhost:27017')
db=client.indeed

metiers = ['développeur', 'data scientist', 'data analyst', 'business intelligence']
localisations = ['Paris', 'Lyon', 'Toulouse', 'Nantes', 'Bordeau', 'Nancy']
contrats = ['permanent', 'contract', 'temporary', 'custom_1', 'apprenticeship', 'internship', 'subcontract', 'fulltime', 'parttime']

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
    test = True
    if len(contrat) > 0:
        while test:
            try:
                page = rq.get(f"https://www.indeed.fr/emplois?q={metier}&l={localisation}&jt={contrat}")
                test = False
            except:
                print('except')
                time.sleep(2)
                test = True
    else:
        while test:
            try:
                page = rq.get(f"https://www.indeed.fr/emplois?q={metier}&l={localisation}")
                test = False
            except:
                print('except')
                time.sleep(2)
                test = True
    soup = bs(page.content, 'html.parser')
    td = soup.find('td', id='resultsCol')
    if len(td.find_all('div', {'class':'invalid_location'})) > 0 or len(td.find_all('div', {'class':'no_results'})) > 0:
        print('Pas de métier trouvé pour cette recherche.')
    # while len(td.find_all('div', {'class':'invalid_location'})) > 0 or len(td.find_all('div', {'class':'no_results'})) > 0:
    #     if len(td.find_all('div', {'class':'invalid_location'})) > 0:
    #         print("La localisation demandé n'a pas pu être trouvé probablement dû à une faute d'orthographe. \nVeuillez rééssayer.")
    #         metier, localisation, contrat = ask(metier=metier, contrat=contrat)
    #     elif len(td.find_all('div', {'class':'no_results'})) > 0:
    #         print(f"Aucun emploi correspondant à la recherche : {metier} à {localisation} avec votre type de contrat, veuillez recommencer.")
    #         metier, localisation, contrat = ask()
    #     page = rq.get(f"https://www.indeed.fr/emplois?q={metier}&l={localisation}&jt={contrat}")
    #     soup = bs(page.content, 'html.parser')
    #     td = soup.find('td', id='resultsCol')
    else:
        print('Vérification valide.')
    return soup

def id_exist(id_test):
    return db['data'].count_documents({'_id':id_test}) > 0

def id_link_title(soup, job):
    td = soup.find('td', id='resultsCol')
    for a in td.find_all('a', rel='noopener nofollow'):
        if id_exist(a.find_parent('div')['data-jk']) == False or a.find_parent('div')['data-jk'] in job['id']:
            job['id'].append(a.find_parent('div')['data-jk'])
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
        test = True
        while test:
            try:
                page = rq.get(link)
                test = False
            except:
                print('except')
                time.sleep(2)
                test = True
        soup_temp = bs(page.content, 'html.parser')
        for div in soup_temp.find_all('div', {'class':'jobsearch-JobMetadataFooter'}):
            for child in div.find_all('div'):
                child.decompose()
            job['publication'].append(div.get_text().split(' - ')[1])
        if soup_temp.find_all('div', {'id':'jobDescriptionText'}) == []:
            job['description'].append('')
        else:
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

def get_next_page(soup, i, metier, localisation, contrat):
    test = True
    while test :
        try:
            page = rq.get(f"https://www.indeed.fr/emplois?q={metier}&l={localisation}&jt={contrat}&start={i}")
            test = False
        except :
            print('except')
            time.sleep(2)
            test = True
    next_soup = bs(page.content, 'html.parser')
    return next_soup

def suivant(soup, metier, localisation, contrat):
    for i in range(10, 110, 10):
        td = soup.find('td', id='resultsCol')
        if td.find_all('a', rel='noopener nofollow') == None:
            break
        else:
            job = reset_job()
            job['ville_recherche'] = localisation
            job['metier_recherche'] = metier
            job['contrat_recherche'] = contrat
            next_soup = get_next_page(soup, i, metier, localisation, contrat)
            id_link_title(next_soup, job)
            get_company(next_soup, job)
            get_adress(next_soup, job)
            with_links(job['lien'], job)
            add_db(job)
              
def add_db(job):
    for i in range(len(list(job.values())[0])):
        if not id_exist(job['id'][i]):
            to_add = {
                '_id':job.get('id')[i],
                'lien':job.get('lien')[i],
                'poste':job.get('poste')[i],
                'entreprise':job.get('entreprise')[i],
                'contrat':job.get('contrat')[i],
                'lieu':job.get('lieu')[i],
                'salaire':job.get('salaire')[i],
                'publication':job.get('publication')[i],
                'description':job.get('description')[i],
                'contrat_recherche':job.get('contrat_recherche'),
                'metier_recherche':job.get('metier_recherche'),
                'ville_recherche':job.get('ville_recherche')

            }
            db['data'].insert_one(to_add)

def reset_job():
    job = {
        'id':[], 'lien':[], 'poste':[], 
        'entreprise':[], 'contrat':[], 'lieu':[], 
        'salaire':[], 'publication':[], 'description':[],
        'metier_recherche':[], 'ville_recherche':[], 'contrat_recherche':[]
        }
    return job

def run():
    for metier in metiers:
        for localisation in localisations:
            for contrat in contrats:
                print('Début pour %s à %s en %s'%(metier, localisation, contrat))
                job = reset_job()
                job['ville_recherche'] = localisation
                job['metier_recherche'] = metier
                job['contrat_recherche'] = contrat
                soup = verification(metier, localisation, contrat)
                id_link_title(soup, job)
                get_company(soup, job)
                get_adress(soup, job)
                with_links(job['lien'], job)
                add_db(job)
                suivant(soup, metier, localisation, contrat)
            print('Fin contrat pour %s à %s'%(metier, localisation))
        print('Fin localisation pour %s'%(metier))
    print('Fin. Youpi')
    
run()

client.close()