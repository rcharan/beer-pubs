import sys
sys.path.append('..')

import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlalchemy
import config
import time


from sqlalchemy.exc import DBAPIError
# from mysql.connector.errors import ProgrammingError
import mysql

import requests
from bs4 import BeautifulSoup
import pandas as pd
from db import db, query, query_list
import config
from selenium import webdriver

################################################################################
#
# Part 1 : Handle fetching a resource from the web
#
#
################################################################################


def get_soup_with_requests(url):
    response = requests.get(url, timeout=5)
    return BeautifulSoup(response.content, 'html.parser')



def get_selenium_resource(setup_process = None):
    '''
    Get a selenium broswer instance

    Open a chromedriver browser. Return a function that acts as a
    resource getter: it takes a url, then returns the browser as a resource
    for a parser

    Returns:
     - a function taking a url and returning a browser instance with
       that page loaded
    '''
    options = webdriver.ChromeOptions()
    options.add_argument(f'user-data-dir=./')

    chromedriver_path = config.chromedriver_location
    browser = webdriver.Chrome(executable_path  = chromedriver_path,
                               options          = options)



    def resource(url):
        browser.get(url)
        return browser

    return resource

################################################################################
#
# Part 2 : Generic function implementing error handling for
#           fetching, parsing, and inserting data
#
################################################################################

def create_scraper(parser, inserter, fetcher):
    # Returns nothing, silently, on success
    # Raises an error when there is no data to lose
    # Returns relevant data when raising an error would lose data
    # Return values must be properly handled by caller
    # kwargs are passed to both parser and inserter, which must accept them
    # url is always passed as a kwarg
    def fetch(url, **kwargs):
        # Make the url available to parser and inserter
        kwargs['url'] = url

        # Get the HTTP response
        try:
            resource = fetcher(url)
        except:
            print('Failed to fetch data; terminating with error')
            raise

        # Parse the returned resource
        try:
            df = parser(resource, **kwargs)
        except Exception as e:
            print('Error parsing; possibly unanticipated data structure')
            print('Returning resource')
            print(e)
            return {'resource' : resource}

        # Insert the df
        try:
            inserter(df, **kwargs)
        except Exception as e:
            print('Error inserting')
            print('Returning resource, parsed df')
            print(e)
            return {'resource' : resource,
                    'df'       :  df}

    return fetch

################################################################################
#
# Part 4 : Generic function for scraping a lot of pages
#
################################################################################

def iterate_scraping(scraper, input_list, sleep_time = 0.1, on_fail = 'abort'):
    for page in input_list:
        error_data = scraper(page)

        # Scraper returns None on success, data on failure
        #  This handles failures
        if error_data and on_fail == 'abort':
            print('Aborting Loop')
            return(error_data)
        elif error_data:
            print( '\n')
            print( '--------------------WARNING----------------------------')
            print( 'See error message above                                ')
            print(f'Proceeding to parse; possible data loss of input {page}')
            print('\n\n')
        else:
            print(f'Successfully scraped with input {page}')
            time.sleep(sleep_time)

################################################################################
#
# Part 5 : Generic function for building a list of targets to scrape
#            excluding those already scraped
#
################################################################################


def get_missing_scrape_targets(target_list, query_col, query_table):
    try:
        have_list = query_list(query_col, query_table, distinct = True)
    except DBAPIError as e:
        if isinstance(e.orig, mysql.connector.errors.ProgrammingError):
            to_do = target_list
            print(f'Unable to detect the database, assuming it is empty and'
                  f' no scraping has yet occured.\n'
                  f'Please confirm that the error message below matches')
            print(e._message())
        else:
            raise e
    else:
        difference = set(target_list).difference(have_list)
        to_do = list(difference)
        print(f'{len(have_list)} pages already scraped detected')

    print(f'{len(to_do)} pages needing scraping detected')
    return to_do

################################################################################
#
# Part 5 : Generic function for inserting into the database
#
################################################################################

# Insert into the database
def make_db_inserter(table_name):
    def insert_df(df, **kwargs):
        df.to_sql(table_name, db, index = False, if_exists = 'append')

    return insert_df
