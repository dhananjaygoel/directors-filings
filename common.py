import nltk
from nltk.tag.stanford import StanfordNERTagger
import re,os
import unicodedata
#nltk.download()
current_dir = os.path.abspath(os.path.dirname(__file__))
st = StanfordNERTagger(current_dir+'/stanford-ner-4.0.0/classifiers/english.all.3class.distsim.crf.ser.gz', current_dir+'/stanford-ner-4.0.0/stanford-ner.jar')

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



def extract_names(text):
    names = [] 
    for sent in nltk.sent_tokenize(text):
        tokens = nltk.tokenize.word_tokenize(sent)
        tags = st.tag(tokens)
        for tag in tags:
            if tag[1]=='PERSON': 
                names.append(tag[0])
    
    name  =''
    for i in names:
        name += i+' '
    return name
    