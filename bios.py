# import our libraries
import re
import requests
import os
import unicodedata
from bs4 import BeautifulSoup
from IPython.display import display
import mysql.connector, requests, os, os.path
from mysql.connector import Error, errorcode
from datetime import datetime
import sys   
import nltk
os.environ['CLASSPATH'] = 'stanford-ner-4.0.0/stanford-ner.jar'
from nltk.tag import StanfordNERTagger
# os.getenv('CLASSPATH') = '../Downloads/stanford-postagger.jar'
# nltk.download()
st = StanfordNERTagger('stanford-ner-4.0.0/classifiers/english.all.3class.distsim.crf.ser.gz') 
# print(st.tag('Rami Eid is studying at Stony Brook University in NY'.split()) )
sys.setrecursionlimit(1000)

# rootdir = os.getcwd() + '/mnt'
# for subdir, dirs, files in os.walk(rootdir):
#     for file in files:
#         print(dirs,file)
def restore_windows_1252_characters(restore_string):
    """
        Replace C1 control characters in the Unicode string s by the
        characters at the corresponding code points in Windows-1252,
        where possible.
    """
    def to_windows_1252(match):
        try:
            return bytes([ord(match.group(0))]).decode('windows-1252')
        except UnicodeDecodeError:
            # No character at the corresponding code point: remove it.
            return ''
        
    return re.sub(r'[\u0080-\u0099]', to_windows_1252, restore_string)
try:
    mydb = mysql.connector.connect(host='172.104.7.112',
                                         database='edgarDataLatest',
                                         user='reguser',
                                         password='Edgar@2020')
    mycursor = mydb.cursor(buffered=True)

    mycursor.execute("SELECT filingtype, name, MAX(CAST(filingdate AS datetime)) FROM edgarapp_filing GROUP BY filingtype, name HAVING filingtype = %s ORDER BY name", ['DEF 14A'])

    myresult = mycursor.fetchall()

    mydb.close()

    
    for filingtype, company, date in myresult:
        # with open('/Users/Adarshr/ExarNorth/working.txt', 'a+') as file:
        #     contents = open('working.txt', 'r').read().splitlines()
        #     print(contents)
        #     search_word = company
        #     print('start searching', search_word)
        #     if search_word in contents:
        #         print ("already found directors")
        #     else:
        #         print('adding potential filings')
        if (filingtype == 'DEF 14A' and str(company).upper() > 'BOSTON BEER CO INC'):
            mydb = mysql.connector.connect(host='172.104.7.112',
                                         database='edgarData',
                                         user='reguser',
                                         password='Edgar@2020')
            mycursor = mydb.cursor(buffered=True)
            date = str(date)
            date = date.split(' ')[0]
            mycursor.execute("SELECT filingpath FROM edgarapp_filing WHERE name = %s AND filingdate = %s", [company, date])
            # print(name, mycursor.fetchall()[0][0])
            path = mycursor.fetchall()[0][0]
            parts = path.split('/')
            dateRemove = parts[1][11:len(parts[1])]
            nums = dateRemove.split('.')
            accession = nums[0]
            full_accession = accession.replace('-', '')
            today = datetime.today()
            if str(today.year) == date.split('-')[0]:
                mycursor.execute("SELECT bio FROM edgarapp_directors WHERE company = %s", [company])
                b = mycursor.fetchall()
                print(b, company, date)
                if all(x[0] == None for x in b) or mycursor.rowcount == 0:
                    new_html_text = r"https://www.sec.gov/Archives/edgar/data/" + parts[0] + '/' + full_accession + '/' + dateRemove
                    print('#######################STARTING NEW FILE###############################')
                    print(new_html_text)
                    # new_html_text = r'https://www.sec.gov/Archives/edgar/data/4281/000110465920053271/0001104659-20-053271.txt'

                    # grab the response
                    response = requests.get(new_html_text)

                    # pass it through the parser, in this case let's just use lxml because the tags seem to follow xml.
                    try:
                        soup = BeautifulSoup(response.content, 'lxml')

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
                                all_thematic_breaks = filing_doc_text.find_all('hr', {'width':'100%'})

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
                                # include below if we ever include the section to store all the page numbers
                                # print('There was {} page(s) found.'.format(len(all_page_numbers)))
                                print('There was {} thematic breaks(s) found.'.format(len(all_thematic_breaks)))

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
                            # print('-'*80)
                            # print('Pulling document {} for text normilzation.'.format(document_id))
                            
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
                                    print(page_soup)

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
                        # print(filing_documents['DEF 14A']['pages_code'])
                        # loop through each document
                        for document_id in filing_documents:
                            
                            # let's grab the all pages code.
                            pages_dict = filing_documents[document_id]['pages_code']  

                             # initalize a dictionary to store all the anchors we find.
                            director_tables_dict = {}
                            done = False
                            checked = {}
                            try:
                                mycursor.execute('SELECT director FROM edgarapp_directors WHERE company = %s', [company])
                                if mycursor.rowcount != 0:
                                    results = mycursor.fetchall()
                                    for directorM in results:
                                        director = directorM[0].split(' ')[-1]
                                        director = director.replace('director', '')
                                        director = director.replace('independent', '')
                                        checked[director] = False
                            except mysql.connector.Error as e:
                                print('MySQL error is: {}'.format(e))
                                mydb.rollback() 
                            if document_id == 'DEF 14A':
                                # loop through each page
                                # print(pages_dict)

                                print(checked, 'first search')
                                for page_num in pages_dict:
                                    
                                    # grab the actual text
                                    page_code = pages_dict[page_num]
                                    
                                    try:
                                        mycursor.execute('SELECT director FROM edgarapp_directors WHERE company = %s', [company])
                                        if mycursor.rowcount != 0:
                                            results = mycursor.fetchall()
                                            for directorM in results:
                                                director = directorM[0].split(' ')[-1]
                                                director = director.replace('director', '')
                                                director = director.replace('independent', '')
                                                # print(director)
                                                for element in page_code.find_all(['p', 'font', 'td']):
                                                    # print(page_code.text)
                                                    if not checked[director] and (director in element.text and ('served' in element.text or 'retired' in element.text)):
                                                        print('starting', director)
                                                        # print(page_code.text)
                                                        try:
                                                            pre, key, post = element.text.partition(director)
                                                            print(director, post)
                                                            post = post.replace('<BR>', "")
                                                            post = post.replace('\xa0', " ")
                                                            checked[director] = True
                                                            mycursor.execute('UPDATE edgarapp_directors SET bio = %s WHERE company = %s AND director = %s', [post, company, directorM[0]])
                                                            mydb.commit()

                                                        except ValueError as e:
                                                            print('empty string')
                                    except mysql.connector.Error as e:
                                        print('MySQL error is: {}'.format(e))
                                        mydb.rollback() 

                                print(checked, 'second search')
                                for page_num in pages_dict:
                                    
                                    # grab the actual text
                                    page_code = pages_dict[page_num]
                                    
                                    try:
                                        mycursor.execute('SELECT director FROM edgarapp_directors WHERE company = %s', [company])
                                        if mycursor.rowcount != 0:
                                            results = mycursor.fetchall()
                                            for directorM in results:
                                                director = directorM[0].split(' ')[-1]
                                                director = director.replace('director', '')
                                                director = director.replace('independent', '')
                                                # print(director)
                                                for element in page_code.find_all(['p', 'font', 'td']):
                                                    # print(page_code.text)
                                                    if not checked[director] and (director in element.text and ('director' in element.text)):
                                                        print('starting', director)
                                                        # print(page_code.text)
                                                        try:
                                                            pre, key, post = element.text.partition(director)
                                                            print(director, post)
                                                            post = post.replace('<BR>', "")
                                                            post = post.replace('\xa0', " ")
                                                            checked[director] = True
                                                            mycursor.execute('UPDATE edgarapp_directors SET bio = %s WHERE company = %s AND director = %s', [post, company, directorM[0]])
                                                            mydb.commit()
                                                        except ValueError as e:
                                                            print('empty string')
                                    except mysql.connector.Error as e:
                                        print('MySQL error is: {}'.format(e))
                                        mydb.rollback()

                                print(checked, 'third search')
                                for page_num in pages_dict:
                                    
                                    # grab the actual text
                                    page_code = pages_dict[page_num]
                                    
                                    try:
                                        mycursor.execute('SELECT director FROM edgarapp_directors WHERE company = %s', [company])
                                        if mycursor.rowcount != 0:
                                            results = mycursor.fetchall()
                                            for directorM in results:
                                                director = directorM[0].split(' ')[-1]
                                                director = director.replace('director', '')
                                                director = director.replace('independent', '')
                                                # print(director)
                                                for element in page_code.find_all(['p', 'font', 'td']):
                                                    # print(page_code.text)
                                                    if not checked[director] and (director in element.text and ('experience' in element.text)):
                                                        print('starting', director)
                                                        # print(page_code.text)
                                                        try:
                                                            pre, key, post = element.text.partition(director)
                                                            print(director, post)
                                                            post = post.replace('<BR>', "")
                                                            post = post.replace('\xa0', " ")
                                                            checked[director] = True
                                                            mycursor.execute('UPDATE edgarapp_directors SET bio = %s WHERE company = %s AND director = %s', [post, company, directorM[0]])
                                                            mydb.commit()
                                                        except ValueError as e:
                                                            print('empty string')
                                    except mysql.connector.Error as e:
                                        print('MySQL error is: {}'.format(e))
                                        mydb.rollback()

                                print(checked, 'fourth search')
                                for page_num in pages_dict:
                                    
                                    # grab the actual text
                                    page_code = pages_dict[page_num]
                                    try:
                                        mycursor.execute('SELECT director FROM edgarapp_directors WHERE company = %s', [company])
                                        if mycursor.rowcount != 0:
                                            results = mycursor.fetchall()
                                            if all(value == False for value in checked.values()):
                                                for directorM in results:
                                                    director = directorM[0].split(' ')[-1]
                                                    director = director.replace('director', '')
                                                    director = director.replace('independent', '')
                                                    # print(director)
                                                    for element in page_code.find_all(['div']):
                                                        # print(page_code.text)
                                                        if not checked[director] and (director in element.text and ('served' in element.text or 'retired' in element.text)):
                                                            print('starting', director, checked[director])
                                                            # print(page_code.text)
                                                            try:
                                                                pre, key, post = element.text.partition(director)
                                                                print(director, post)
                                                                post = post.replace('<BR>', "")
                                                                post = post.replace('\xa0', " ")
                                                                checked[director] = True
                                                                mycursor.execute('UPDATE edgarapp_directors SET bio = %s WHERE company = %s AND director = %s', [post, company, directorM[0]])
                                                                mydb.commit()
                                                            except ValueError as e:
                                                                print('empty string')
                                        
                                    except mysql.connector.Error as e:
                                        print('MySQL error is: {}'.format(e))
                                        mydb.rollback()  

                                        
                    except RecursionError as e:
                        print('Recursion error, something went wrong with parsing')
            mydb.close()
except mysql.connector.Error as e:
    print(e)