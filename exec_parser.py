# import our libraries
import re
import requests
import os
import unicodedata
from bs4 import BeautifulSoup
from IPython.display import display
import mysql.connector, requests, os, os.path
from mysql.connector import Error, errorcode
import sys   
import nltk
from datetime import datetime
from nltk.tag.stanford import StanfordNERTagger
from config import *
from common import *

import pymysql

current_dir = os.path.abspath(os.path.dirname(__file__))
st = StanfordNERTagger(current_dir+'/stanford-ner-4.0.0/classifiers/english.all.3class.distsim.crf.ser.gz', current_dir+'/stanford-ner-4.0.0/stanford-ner.jar')


#os.environ['CLASSPATH'] = 'stanford-ner-4.0.0/stanford-ner.jar'
# from nltk.tag import StanfordNERTagger
# os.getenv('CLASSPATH') = '../Downloads/stanford-postagger.jar'
# nltk.download()
# st = StanfordNERTagger('stanford-ner-4.0.0/classifiers/english.all.3class.distsim.crf.ser.gz') 


sys.setrecursionlimit(1000)

try:
    mydb = pymysql.connect(host=host,
                            database=database_name,
                            user=user,
                            password=password,
                            port = port)
    mycursor = mydb.cursor()
    mycursor.execute('select cik,id from edgarapp_companycik')

    for cik,cik_id in mycursor.fetchall():
        
        mycursor.execute(''' SELECT cik,filingpath,filingdate,name FROM edgarapp_proxies  where cik=%s  and filingdate = (
            select max(filingdate) from edgarapp_proxies where cik =%s)''',(cik,cik))
        myresult = mycursor.fetchall()

        for cik, filingpath,filingdate, company  in myresult:

            path = filingpath
            parts = path.split('/')
            dateRemove = parts[1][11:len(parts[1])]
            nums = dateRemove.split('.')
            accession = nums[0]
            full_accession = accession.replace('-', '')
            print(company, filingdate)
            today = datetime.today()

            if True :#str(today.year) == date.split('-')[0]:
                mycursor.execute("SELECT director FROM edgarapp_directors WHERE cik_director_id = %s", [cik_id])
                past_director = mycursor.fetchall()
            
                if True:
                    new_html_text = S3_filing_url + filingpath
                    print('#######################STARTING NEW FILE###############################')
                    print(new_html_text)

                    # grab the response
                    response = requests.get(new_html_text)

                    # pass it through the parser, in this case let's just use lxml because the tags seem to follow xml.
                    try:
                        soup = BeautifulSoup(response.content, 'html5lib')

                        # define a dictionary that will house all filings.
                        master_filings_dict = {}

                        # let's use the accession number as the key. This is Apple's (found from the link)
                        accession_number = '1'

                        # add a new level to our master_filing_dict, this will also be a dictionary.
                        master_filings_dict[accession_number] = {}

                        # this dictionary will contain two keys, the sec header content, and a documents key.
                        master_filings_dict[accession_number]['sec_header_content'] = {}
                        master_filings_dict[accession_number]['filing_documents'] = None

                        # grab the sec-header tag, so we can store it in the master filing dictionary.
                        sec_header_tag = soup.find('sec-header')

                        # store the tag in the dictionary just as is.
                        master_filings_dict[accession_number]['sec_header_content']['sec_header_code'] = sec_header_tag

                        # display the sec header tag, so you can see how it looks.
                        # display(sec_header_tag)

                        master_document_dict = {}

                        # find all the documents in the filing.
                        for filing_document in soup.find_all('document'):
                            
                            # needed to inlcude find(type) because DEF 14A files have a space, don't need to do this otherwise
                            # define the document type, found under the <type> tag, this will serve as our key for the dictionary.
                            document_id = filing_document.find(type).find(text=True, recursive=False).strip()
                            display(document_id)

                            # here are the other parts if you want them.
                            document_sequence = filing_document.sequence.find(text=True, recursive=False).strip()
                            document_filename = filing_document.filename.find(text=True, recursive=False).strip()
                            # 13Fs do not have a document description
                            # document_description = filing_document.description.find(text=True, recursive=False).strip()
                            
                            if document_id not in master_document_dict and document_id != 'GRAPHIC':
                                # initalize our document dictionary
                                master_document_dict[document_id] = {}
                                # add the different parts, we parsed up above.
                                master_document_dict[document_id]['document_sequence'] = document_sequence
                                master_document_dict[document_id]['document_filename'] = document_filename
                                # 13Fs do not have a document description
                                # master_document_dict[document_id]['document_description'] = document_description
                                # store the document itself, this portion extracts the HTML code. We will have to reparse it later.
                                master_document_dict[document_id]['document_code'] = filing_document.extract()
                                
                                
                                # grab the text (between text tags) portion of the document, this will be used to split the document into pages.
                                filing_doc_text = filing_document.find('text').extract()

                                
                                # find all the thematic breaks, these help define page numbers and page breaks.
                                all_thematic_breaks = filing_doc_text.find_all('hr',{'width':'100%'})

                                 # convert all thematic breaks to a string so it can be used for parsing
                                all_thematic_breaks = [str(thematic_break) for thematic_break in all_thematic_breaks]
                                
                                # prep the document text for splitting, this means converting it to a string.
                                filing_doc_string = str(filing_doc_text)
                                
                                # handle the case where there are thematic breaks.
                                if len(all_thematic_breaks) > 0:
                                
                                    # define the regex delimiter pattern, this would just be all of our thematic breaks (denote thematic breaks via '|').
                                    regex_delimiter_pattern = '|'.join(map(re.escape, all_thematic_breaks))

                                    # split the document along each thematic break.
                                    split_filing_string = re.split(regex_delimiter_pattern, filing_doc_string)

                                    # store the document itself
                                    master_document_dict[document_id]['pages_code'] = split_filing_string

                                # handle the case where there are no thematic breaks.
                                elif len(all_thematic_breaks) == 0:

                                    # handles so it will display correctly.
                                    split_filing_string = all_thematic_breaks
                                    
                                    # store the document as is, since there are no thematic breaks. In other words, no splitting.
                                    master_document_dict[document_id]['pages_code'] = [filing_doc_string]
                                # display some information to the user.
                                # print('-'*80)
                                # print('The document {} was parsed.'.format(document_id))
                                # # include below if we ever include the section to store all the page numbers
                                # # print('There was {} page(s) found.'.format(len(all_page_numbers)))
                                # print('There was {} thematic breaks(s) found.'.format(len(all_thematic_breaks)))

                        # store the documents in the master_filing_dictionary.
                        master_filings_dict[accession_number]['filing_documents'] = master_document_dict
                        # print(master_filings_dict[accession_number]['filing_documents']['DEF 14A']['pages_code'])

                        # print(master_document_dict)
                        print('-'*80)
                        print('All the documents for filing {} were parsed and stored.'.format(accession_number))

                        # first grab all the documents
                        filing_documents = master_filings_dict[accession_number]['filing_documents']
                       
                        # loop through each document
                        for document_id in filing_documents:
                            # display some info to give status updates.
                            print('-'*80)
                            print('Pulling document {} for text normilzation.'.format(document_id))
                            
                            # grab all the pages for that document
                            document_pages = filing_documents[document_id]['pages_code']

                            # page length
                            pages_length = len(filing_documents[document_id]['pages_code'])
                            
                            # initalize a dictionary that'll house our repaired html code for each page.
                            repaired_pages = {}
                            
                            # initalize a dictionary that'll house all the normalized text.
                            normalized_text = {}

                            # loop through each page in that document.
                            for index, page in enumerate(document_pages):
                                
                                # pass it through the parser. NOTE I AM USING THE HTML5 PARSER. YOU MUST USE THIS TO FIX BROKEN TAGS.
                                page_soup = BeautifulSoup(page,'html5lib')

                                # grab all the text, notice I go to the BODY tag to do this
                                try:
                                    page_text = page_soup.html.body.get_text(' ',strip = True)
                                except:
                                    print('error',page_soup)

                                # print(page_text)

                                # normalize the text, remove messy characters. Additionally, restore missing window characters.
                                page_text_norm = restore_windows_1252_characters(unicodedata.normalize('NFKD', page_text)) 
                                
                                # Additional cleaning steps, removing double spaces, and new line breaks.
                                page_text_norm = page_text_norm.replace('  ', ' ').replace('\n',' ')

                                # print(page_text_norm)

                                    # define the page number.
                                page_number = index + 1
                                
                                # add the normalized text to the list.
                                normalized_text[page_number] = page_text_norm
                                
                                # add the repaired html to the list. Also now we have a page number as the key.
                                repaired_pages[page_number] = page_soup
                            
                                # display a status to the user
                                # print('Page {} of {} from document {} has had their text normalized.'.format(index + 1, pages_length, document_id))

                                # add the normalized text back to the document dictionary
                                filing_documents[document_id]['pages_normalized_text'] = normalized_text
                                
                                # add the repaired html code back to the document dictionary
                                filing_documents[document_id]['pages_code'] = repaired_pages
                                
                                # define the generated page numbers
                                gen_page_numbers = list(repaired_pages.keys())
                                
                                # add the page numbers we have.
                                filing_documents[document_id]['pages_numbers_generated'] = gen_page_numbers    
                                
                            # display a status to the user.
                            print('All the pages from document {} have been normalized.'.format(document_id))

                        # print(master_filings_dict[accession_number]['filing_documents']['DEF 14A']['pages_code'])


                        #######################################
                        ####### TABLE SEARCH AND SCRAPE #######
                        #######################################


                        # first grab all the documents
                        filing_documents = master_filings_dict[accession_number]['filing_documents']

                        def scrape_table_dictionary(table_dictionary):
                            
                            # initalize a new dicitonary that'll house all your results
                            new_table_dictionary = {}
                            if len(table_dictionary) != 0:

                                # loop through the dictionary
                                for table_id in table_dictionary:

                                    # grab the table
                                    table_html = table_dictionary[1]
                                    # print(table_html)
                                    # grab all the rows.
                                    table_rows = table_html.find_all('tr')
                                    
                                    # parse the table, first loop through the rows, then each element, and then parse each element.
                                    parsed_table = [
                                        [element.get_text(strip=True) for element in row.find_all('td')]
                                        for row in table_rows
                                    ]
                                    
                                    # keep the original just to be safe.
                                    new_table_dictionary[table_id] = {}

                                    # new_table_dictionary[table_id]['original_table'] = table_html
                                    
                                    # add the new parsed table.
                                    # new_table_dictionary[table_id]['parsed_table'] = parsed_table
                                    
                                    # here some additional steps you can take to clean up the data - Removing '$'.
                                    # parsed_table_cleaned = [
                                    #     [element for element in row if element != '$']
                                    #     for row in parsed_table
                                    # ]
                                    
                                    # here some additional steps you can take to clean up the data - Removing Blanks.
                                    parsed_table_cleaned = [
                                        [element for element in row if element != None and element != '']
                                        for row in parsed_table
                                    ]



                                    new_table_dictionary[table_id]['parsed_table_cleaned'] = parsed_table_cleaned
                                    new_table_dictionary[table_id]['parsed_table'] = parsed_table

                                    
                            else:
                                new_table_dictionary[1] = {}
                                # if there are no tables then just have the id equal NONE
                                # new_table_dictionary[1]['original_table'] = None
                                new_table_dictionary[1]['parsed_table'] = None
                                new_table_dictionary[1]['parsed_table_cleaned'] = None
                                
                            return new_table_dictionary

                        # loop through each document
                        for document_id in filing_documents:
                            # get all the pages code in a particular document
                            pages_dict = filing_documents[document_id]['pages_code']
                            if document_id == 'DEF 14A':
                                # something to store the tables we find
                                tables_dict = {}

                                for page_num in pages_dict:

                                    # get a page's code
                                    page_code = pages_dict[page_num]
                                    # find all the tables
                                    tables_found = page_code.find_all('table')

                                    # number of tables found
                                    num_found = len(tables_found)

                                    # store in tables_dict
                                    # each page is going to be checked, so let's have another dictionary that'll house all the tables found.
                                    tables_dict[page_num] = {(table_id + 1): table for table_id, table in enumerate(tables_found)}   

                                    # display a status to the user.
                                    # print('Page {} of {} from document {} contained {} tables.'.format(page_num, document_id, num_found))

                                # display a status to the user.  
                                print('All the pages from document {} have been scraped for tables.'.format(document_id)) 
                                print('-'*80)   
                                for page_num in pages_dict:
                                    tables_dict[page_num] = scrape_table_dictionary(tables_dict[page_num])
                                # let's add the matching tables dict to the document.
                                filing_documents[document_id]['table_search'] = tables_dict
                            # print(filing_documents['DEF 14A']['table_search'])

                        #######################################
                        ####### DIRECTOR SEARCH AND SCRAPE ########
                        #######################################


                        # first grab all the documents
                        filing_documents = master_filings_dict[accession_number]['filing_documents']
                        #print(filing_documents)
                        for document_id in filing_documents:
                            
                            # let's grab the all pages code.
                            pages_dict = filing_documents[document_id]['pages_code']  

                             # initalize a dictionary to store all the anchors we find.
                            director_tables_dict = {}
                            done = False
                            # loop through each page
                            # print(pages_dict)
                            for page_num in pages_dict:
                                
                                # grab the actual text
                                page_code = pages_dict[page_num]
                                
                                # find all the anchors in the page, that have the attribute 'name'
                                htmlTags = ['b','p', 'font', 'div', 'a', 'table']
                                directors_found = page_code.find_all(htmlTags)
                                for element in directors_found:
                                    matches = ['Director','Compensation']
                                    matchesOne = ['DIRECTOR','COMPENSATION']
                                    matchesTwo = ['Directors', 'Compensation']
                                    matchesThree = ['DIRECTORS','COMPENSATION']
                                    matchesFour = ['Non-Employee', 'Director']
                                    matchesFive = ['Trustee', 'Compensation']
                                    matchesSix = ['TRUSTEE', 'COMPENSATION']
                
                                    if done == False and (all(x in element.text for x in matches) or all(x in element.text for x in matchesTwo) or all(x in element.text for x in matchesThree) or all(x in element.text for x in matchesOne) or all(x in element.text for x in matchesFour) or all(x in element.text for x in matchesFive) or all(x in element.text for x in matchesSix)): 
                                        # print(filing_documents[document_id]['table_search'][page_num])
                                        #print(page_code,'page_code')
                                        #print(page_num,'page_num')
                                        tables = page_code.find_all('table')
                                        
                                        for table in tables:
                                            if done == False:
                                                table_rows = table.find_all('tr')
                                                # parse the table, first loop through the rows, then each element, and then parse each element.
                                                director_table_unclean = [
                                                    [element.get_text(strip=True) for element in row.find_all(['td', 'th'])]
                                                    for row in table_rows
                                                ]
                                                director_table_cleaned = [
                                                    [element for element in row if element != None and element != '']
                                                    for row in director_table_unclean
                                                ]

                                                director_table_cleaned = [i for i in director_table_cleaned if i != []]

                                                director_table_cleaned = [[j.lower() for j in i] for i in director_table_cleaned]

                                                director_table_cleaned = [[j for j in i if j != '\u200b'] for i in director_table_cleaned]
                                                
                                                director_table_cleaned = [[j.replace('\xa0', " ") for j in i] for i in director_table_cleaned]

                                                director_table_cleaned = [[j.replace('<br>', "") for j in i] for i in director_table_cleaned]


                                                director_table_cleaned = [i for i in director_table_cleaned if i != []]

                                                #print(director_table_cleaned)

                                                director_table_cleaned = [i for i in director_table_cleaned if len(i) > 1]
                                                
                                                directors = []
                                                
                                                #print(director_table_cleaned)
                                                try:
                                                    if any('beneficial owner' in s for s in director_table_cleaned[0]) or any('fees earned' in s for s in director_table_cleaned[0]) or any("name" in s and len(s) < 8 for s in director_table_cleaned[0]) or any('total' in s for s in director_table_cleaned[0]) or any('trust' in s for s in director_table_cleaned[0]) or any('director' in s for s in director_table_cleaned[0]) and not any('year' in s for s in director_table_cleaned[0]):
                                                        # print(director_table_cleaned[0])
                                                        if (any("stock" in s for s in director_table_cleaned[0]) or any("awards" in s for s in director_table_cleaned[0]) or any("fees earned" or "feesearned" in s for s in director_table_cleaned[0]) or any("aggregate" in s for s in director_table_cleaned[0]) ) and not (any('outstanding' in s for s in director_table_cleaned[0]) or any('unearned' in s for s in director_table_cleaned[0]) or any('executive' in s for s in director_table_cleaned[0]) or any('principal' in s for s in director_table_cleaned[0])):
                                                            # print(director_table_cleaned)
                                                            # print('starting', done)
                                                            for element in director_table_cleaned:
                                                                directors.append(element[0])
                                                            # print(directors)
                                                            directors = [s.replace(')', '') for s in directors]
                                                            directors = [s.replace('(', '') for s in directors]
                                                            directors = [s.replace(',', '') for s in directors]
                                                            directors = [s.replace('jr.', '') for s in directors]
                                                            directors = [''.join(i for i in s if not i.isdigit()) for s in directors]
                                                            directors = [s.title() for s in directors]
                                                            # print(directors)
                                                            cleaned = []
                                                            peoples = []
                                                            for element in directors:
                                                                name = extract_names(element)
                                                                # print(tokens, tags)
                                                                #if all(tag[1] == 'PERSON' for tag in tags):
                                                                #    name = ' '.join(tag[0] for tag in tags if tag[0][len(tag[0]) - 1] != '.' and (tag[0] != 'I') and tag[0] != 'Ii' and tag[0] != 'Iii' and tag[0] != 'Namea')
                                                                if len(name)!=0:
                                                                    cleaned.append(name)
                                                            if len(cleaned) > 2:
                                                                done = True
                                                                print('directors', done)
                                                                print(cleaned)
                                                                que = f"select * from  edgarapp_directors where cik_director_id= {cik_id}"
                                                                mycursor.execute(que)
                                                                if len(mycursor.fetchall()) !=0 and len(cleaned) != 0 :
                                                                    que = f"delete from  edgarapp_directors where cik_director_id= {cik_id}"
                                                                    mycursor.execute(que)
                                                                    

                                                                for person in cleaned:
                                                                    data = [company, person,cik_id]
                                                                    try:
                                                                        # print('entering {} into db.'.format(data))
                                                                        mycursor.execute("INSERT INTO edgarapp_directors (company, director,cik_director_id) VALUES (%s, %s,%s)", data)
                                                                        # print('finished entering')
                                                                        mydb.commit()
                                                                    except mysql.connector.Error as e:
                                                                        print('MySQL error is: {}'.format(e))
                                                                        mydb.rollback()  


                                                except Exception as e:
                                                    print('exception occured',e)
                                                    l = 3
                    except RecursionError as e:
                        print('Recursion error, something went wrong with parsing')
                else:
                    print('directors for {} already stored in database'.format(company))
            #mydb.close()
except mysql.connector.Error as e:
    print(e)
