# directors-filings

## STEPS:
1. clone reprository https://github.com/dhananjaygoel/directors-filings
2. Download db backup from the link https://drive.google.com/file/d/1Vqk9wKFTWdX97DUfTPmXUU88fEztzsdi/view?usp=sharing
3. Create database and restore the db
4. update variables present in config.py file based on your db configuration
```python
    database_name = 'yourdbname'
    port = dbport
    host = 'dbhost'
    password = 'dbpassword'
    user = 'dbuser'
```
5. Download python libraries present in requirements.txt
    ```python
        pip install requirements.txt
    ```
6.  Run the file exec_parser.py to fetch directors name from the proxy file and store in db
    ```python
        python exec_parser.py
    ```
7.  Run the file ages.py to fetch director's age from the proxy file and store in db
    ```python
        python age.py
    ```

6.  Run the file bio.py to fetch director's bio from the proxy file and store in db
    ```python
        python bio.py
    ```

## Files Description
1. exce_parser.py :
    This script extracts director name and store in db
2. ages.py
    This script extracts age info of the directors and update db
3. bios.py
    This script extract bio of the directors and update db
4. config.py 
    This file contains database settings.
    Update it based on your local db