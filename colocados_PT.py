# -*- coding: utf-8 -*-
"""
Created on Sun Sep  8 08:48:21 2019

@author: Bruno
"""

import urllib3
from string import ascii_uppercase
from lxml import  etree

assigned_db   = []
candidates_db = []
courses_db    = []

def unique(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]

opennings_base_url  = 'http://www.dges.gov.pt/guias/indcurso.asp?letra='
assigned_base_url   = 'http://www.dges.gov.pt/coloc/2019/col1listacol.asp'
candidates_base_url = 'http://www.dges.gov.pt/coloc/2019/col1listaser.asp'
base_page           = 'http://www.dges.gov.pt/guias/'

headers = {'User-agent'   : 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.16 Safari/537.36',
           'Content-Type' : 'application/x-www-form-urlencoded',
           'Cookie'       : 'ASPSESSIONIDASDCRASQ=AGNNIKBDGJGIJLKLCIKJHBMD; ASPSESSIONIDSAARDCRR=BMNNGIBDEHJPOEDAGPPGACBN; __utma=69316101.253696569.1505119588.1505119588.1505119711.2; __utmb=69316101.2.10.1505119711; __utmc=69316101; __utmz=69316101.1505119711.2.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not"%"20provided); ASPSESSIONIDCQCQDASQ=MNDPNLBDNAJFIKFKHFANMMEN; ASPSESSIONIDAQRDSATS=EEDGKMADEKMMCCDNEEGOBOAB; ASPSESSIONIDCCDBRBRS=EEJDIHBDPGJMLPOGOAOHMFHD'}

http = urllib3.PoolManager()

for letter in ascii_uppercase:
    
    opennings_url  = opennings_base_url + letter
    opennings_page = http.request('GET', opennings_url)
    opennings_data = opennings_page.data.decode('latin-1')
    opennings_root = etree.HTML( opennings_data )

    # fetch university courses
    courses_codes          = opennings_root.xpath('//div[@class="lin-curso-c3"]/a/@title')
    opennings_courses      = opennings_root.xpath('//div[@class="lin-curso-c4"]/text()')
    university_courses     = opennings_root.xpath('//div[@class="lin-curso-c3"]/a/text()')
    university_courses_url = opennings_root.xpath('//div[@class="lin-curso-c3"]/a/@href')
    
    for id_, course_code in enumerate(courses_codes):
        temp_code       = course_code.split('/')
        university_code = temp_code[0]
        country_code    = temp_code[1]
        
        fields_data     = {'CodCurso':country_code ,'CodEstab':university_code}
        
        # check if this course belongs to a politechnic university, if it is and is valid mark as so
        university_page = http.request('GET',                                  \
                        url = base_page + '/' + university_courses_url[id_],   \
                            headers = headers)
        
        university_page_root = etree.HTML( university_page.data ) 
        university_type_text = university_page_root.xpath('//div[@class="inside2"]/text()')
        university_name      = university_page_root.xpath('//div[@class="cab2"]/text()')[0]
        
        # fetch the line that has Tipo de Ensino
        for line in university_type_text:
            if 'tipo de ensino:' in line.lower():
                university_type = line
                break
        
        assigned_page   = http.request('POST', url = assigned_base_url, headers = headers, fields = fields_data, encode_multipart = False)
        assigned_root   = etree.HTML(assigned_page.data.decode('latin-1'))
        
        assigned        = assigned_root.xpath('//table[@class="caixa"]/tr/td/text()')
        assigned        = [i.replace('\r\n\t\t\t','').replace('\r\n\t\t','').strip() for i in assigned]
        
        if len(assigned) == 0:
            continue
        
        course_designation     = assigned[1]
        university_designation = university_courses[id_]
        
        assigned_ids   = [a for i, a in enumerate(assigned) if i%2 == 0]
        assigned_names = [a for i, a in enumerate(assigned) if i%2 == 1]
        assigned_ids   = assigned_ids[1:]
        assigned_names = assigned_names[1:]
        
        candidates_page      = http.request('POST',url = candidates_base_url,   \
                                        headers = headers, fields = fields_data,\
                                            encode_multipart = False)
        
        candidates_root      = etree.HTML(candidates_page.data)
        number_of_candidates = candidates_root.xpath('//table/tr/td/a/@href')[0]
        
        if 'col1listaser.asp' in number_of_candidates:
            # obtem o mx
            number_of_candidates = number_of_candidates.split('&')
            number_of_candidates = [i for i in number_of_candidates if 'Mx' in i][0]
            
            number_of_candidates = number_of_candidates.replace('Mx=','')
            fields_data['ids']   = '1'
            fields_data['ide']   = number_of_candidates
            fields_data['Mx']    = number_of_candidates
            
            # obtem nova pagina
            candidates_url    = candidates_base_url + '?CodEstab=' + str(university_code) + '&'
            candidates_url    = candidates_url + 'CodCurso=' + str(country_code) + '&'
            candidates_url    = candidates_url + 'Mx=' + number_of_candidates + '&'
            candidates_url    = candidates_url + 'ide='+ number_of_candidates + '&'
            candidates_url    = candidates_url + 'ids=1'
            candidates_page = http.request('GET',url = candidates_url)
            candidates_root = etree.HTML(candidates_page.data.decode('latin-1'))
        
        candidates = candidates_root.xpath('//table/tr/td/text()')
        
        state = 'OK'
        politechnic_state = 'Politécnico'
        
        if not ('Polit' in university_type):
            politechnic_state = 'Superior'
            
        if not candidates:
            state = 'ERROR'
        print(f'{state} {politechnic_state}: {course_designation} -> {university_designation}')
        
        if not candidates:
            continue
        
        
        
        candidates_course_designation = candidates[4]
        candidates = candidates[9:]
        candidates = [candidate.replace('\r\n\t\t\t','').replace('\r\n\t\t','') for candidate in candidates]
        candidates = candidates[0:(len(candidates)-5)]
        
       
        ids_temp = [ i for i, candidate in enumerate(candidates) if '(...)' in candidate]
        ids_candidates = []
        num_id_candidates = []
        name_candidates = []
        grade_candidates = []
        option_candidates = []
        pi_candidates = []
        p12_candidates = []
        p1110_candidates = []
        
        for i in ids_temp:
            ids_candidates.append(candidates[i-1])
            num_id_candidates.append(candidates[i])
            name_candidates.append(candidates[i+1])
            grade_candidates.append(candidates[i+2])
            option_candidates.append(candidates[i+3])
            pi = candidates[i+4]
            if not pi:
                pi = candidates[i+5]
                p12_candidates.append(candidates[i+6])
                p1110_candidates.append(candidates[i+7])
            else:
                p12_candidates.append(candidates[i+5])
                p1110_candidates.append(candidates[i+6])
            pi_candidates.append( pi )
        
        ids_v = []
        for i, name_candidate in enumerate(name_candidates):
            for j, assigned_name in enumerate(assigned_names):
                if name_candidate == assigned_name and num_id_candidates[i] == assigned_ids[j]:
                    ids_v.append(i)
            
        #ids_v = [i for i,name_candidate in enumerate(name_candidates) 
        #            if name_candidate in assigned_names and num_id_candidates[i] in assigned_ids]
        
        if len(set(ids_v)) != len(assigned_names):
            print('ERRO: número de colocados diferente!!!')
            raise StopIteration
            
        for i in ids_v:
            assigned_db.append( { 'num_id'           : num_id_candidates[i],
                                  'nome'             : name_candidates[i], 
                                  'nota'             : grade_candidates[i],
                                  'opcao'            : option_candidates[i],
                                  'pi_candidatos'    : pi_candidates[i],
                                  'nota_12'          : p12_candidates[i],
                                  'nota_10/11'       : p1110_candidates[i], 
                                  'curso_univ'       : university_code,
                                  'curso_pais'       : country_code,
                                  'vagas_curso'      : opennings_courses[id_],
                                  'designacao'       : course_designation, 
                                  'vagas_resultantes': int(opennings_courses[id_])-len(assigned_names),
                                  'tipo_de_universidade' : politechnic_state,
                                  'universidade'     : university_name
                                  })
        for i, temp in enumerate(ids_candidates):
            candidates_db.append({'num_id'           : num_id_candidates[i],
                                  'nome'             : name_candidates[i], 
                                  'nota'             : grade_candidates[i],
                                  'opcao'            : option_candidates[i],
                                  'pi_candidatos'    : pi_candidates[i],
                                  'nota_12'          : p12_candidates[i],
                                  'nota_10/11'       : p1110_candidates[i], 
                                  'curso_univ'       : university_code,
                                  'curso_pais'       : country_code,
                                  'vagas_curso'      : int(opennings_courses[id_]),
                                  'designacao'       : course_designation,
                                  'tipo_de_universidade' : politechnic_state,
                                  'universidade'     : university_name})
    
with open('colocados_db.csv','w', encoding='latin-1') as ft:
    ft.write('num_id,nome,nota,opcao,pi,nota_12,nota_10/11,curso_univ,curso_pais,vagas_curso,designacao,vagas_resultantes,tipo_de_universidade,universidade\n')
    keys = ['num_id','nome','nota','opcao','pi_candidatos','nota_12','nota_10/11','curso_univ','curso_pais','vagas_curso','designacao', 'vagas_resultantes','tipo_de_universidade','universidade']
    for line in assigned_db:0
        for key in keys:
            if key == 'opcao':
                if line[key]:
                    ft.write(line[key].replace(',','.')+',')
                else:
                     ft.write('1,')
            elif key=='vagas_resultantes' or key=='vagas_curso':
                ft.write(str(line[key]).replace(',','.')+',')
            else:
                ft.write(line[key].replace(',','.')+',')
        ft.write('\n')

with open('candidatos_db.csv','w',encoding='latin-1') as ft:
    ft.write('num_id,nome,nota,opcao,pi,nota_12,nota_10/11,curso_univ,curso_pais,vagas_curso,designacao,tipo_de_universidade,universidade\n')
    keys = ['num_id','nome','nota','opcao','pi_candidatos','nota_12','nota_10/11','curso_univ','curso_pais','vagas_curso','designacao','tipo_de_universidade','universidade']
    for line in candidates_db:
        for key in keys:
            if key == 'opcao':
                if line[key]:
                    ft.write(line[key].replace(',','.')+',')
                else:
                     ft.write('1,')
            elif key == 'vagas_resultantes' or key=='vagas_curso':
                 ft.write(str(line[key]).replace(',','.')+',')
            else:
                ft.write(line[key].replace(',','.')+',')
        ft.write('\n')
        
