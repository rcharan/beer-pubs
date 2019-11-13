import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from more_itertools import unique_everseen
import string
import itertools
import re
import sys
sys.path.append('..')
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy  as np
from db import db, query, query_list

################################################################################
#
# Part 1 : Utilities
#
################################################################################


def get_xpath_with_waiting(browser, xpath, time_out = 2, poll_frequency = 0.5):
    return WebDriverWait(browser, time_out,
                             poll_frequency = poll_frequency).until(
                                EC.presence_of_element_located((By.XPATH, xpath))
                            )


################################################################################
#
# Part 2 : The main parser for beer-by-beer information
#
################################################################################


def parse_page(browser, **kwargs):
    # Parse the header
    url    = kwargs['url']
#
    # Parse the bar location
    address = browser.find_element_by_xpath('''//div[./h4[text()='Place Info']]//a''').text

    # Package the meta info for the beer parser
    meta_dict = {
             # 'bar_name'           : bar_name,
             # 'city'               : city,
             # 'establishment_type' : establishment_type,
             # 'neighborhood'       : neighborhood,
             'bar_url'            : url,
             'address'            : address
    }

    # Expand the beer list if it is not all displayed
    expand_buttons = browser.find_elements_by_xpath(
       '''//ul[./lh]/li/a[contains(text(),'View all')]'''
    )
    for button in expand_buttons:
        button.click()
        time.sleep(0.5)

    # Parse the beer list
    groupings = browser.find_elements_by_xpath('//ul[./lh]')
    def parse_grouping(group):
        group_name = group.find_element_by_xpath('lh').text
        beers      = group.find_elements_by_xpath('./li')
        beers      = filter(lambda elt : elt.is_displayed(), beers)
        meta_dict['grouping'] = group_name
        return filter(None, (parse_beer(beer, **meta_dict) for beer in beers))

    beers = itertools.chain.from_iterable(parse_grouping(group) for group in groupings)
    return pd.DataFrame.from_records(beers)

################################################################################
#
# Part 3 : Parse and individual beer
#
#   Structure:
#     Parse beer calls:
#      - parse_beer_name; and
#      - parse_beer_text
#      then packages the result
#
#     Parse_beer_text extracts the paragraphs of texts and passes them to
#      get_par_type_1 and get_par_type_3 to detect and extract information
#      (par_type_2 was removed).
#
#     Each of parse_beer_text and parse_beer_name handles missing values
#      appropriately
#
################################################################################

def parse_beer(beer, **meta_info):
    # Extract the information from the html structure
    beer_name_info = parse_beer_name(beer)
    beer_text_info = parse_beer_text(beer)

    if not beer_name_info:
        print(f'url: {url}')

    return dict(**beer_name_info, **beer_text_info, **meta_info)

def parse_beer_name(beer):
    # Get the beer title: some beers are linked and some are not
    try:
        title = beer.find_element_by_xpath('.//h3/a')
        beer_name = title.text
        beer_url  = title.get_attribute('href')
    except:
        try:
            title = beer.find_element_by_xpath('.//h3/span')
            beer_name = title.text
            beer_url  = None
        except:
            print(f'Error parsing a beer name {beer.text}')
            return {}

    return {'name' : beer_name,
            'beer_url' : beer_url}

@np.vectorize
def get_par_type_1(par):
    '''
      Detects and parses certain beer information

      Specifically paragraphs usually of the form
      (type of beer) · (abv) · (origin)
      with the last sometimes missing. Empirically item 2 is only missing
      if item 3 is; likewise 1 w.r.t. 2
    '''
    sep_char = "·"
    if sep_char not in par:
        return None
    else:
        return dict(zip(['beer_type', 'abv', 'origin'], par.split(sep_char)))

seen_issues = []

@np.vectorize
def get_par_type_3(par, verbose = True):
    '''
      Detects and parses certain beer information

      Specifically paragraphs of the form
      (volume) (type = draft/can/bottle etc.) (price)
      with some of fields possibly missing.

      If verbose = True (default), prints the paragraph when
      some fields exist but others are missing.
    '''
    if len(par.split(' ')) > 6:
        return None

    # Build a regex for the volume
    allowed_units = ['oz', 'cl', 'Liter Keg', 'ml', 'L']
    allowed_non_numeric_vols = ['Pint', '1/\d Keg', '\d\d L Keg']

    allowed_units = '|'.join(allowed_units)
    allowed_non_numeric_vols = '|'.join(allowed_non_numeric_vols)

    vol_re = f'''([0-9.]+(?:{allowed_units})|{allowed_non_numeric_vols})'''

    # Build a regex for the kind
    allowed_kinds = ['Draft', 'Can', 'Bottle', 'Growler',
                     '''Crowler \(can\)''', 'Cask', 'Pitcher', 'By the glass',
                     'Glass', 'Pour', 'Keg']

    allowed_kinds = map(lambda s : f'''((?:\d\d? Pack)?(?:\s|^){s}s?)(?:\s|$)''', allowed_kinds)
    allowed_kinds = '|'.join(allowed_kinds)
    kind_re = f'({allowed_kinds})'

    # Regex for the price
    price_re = '\$([0-9.]*)'

    has_price = re.search(price_re, par)
    has_kind  = re.search(kind_re, par)
    has_vol   = re.search(vol_re, par)


    # Handle missing values by printing and internal logging
    if has_price or has_kind or has_vol:
        if not has_price and verbose and par not in seen_issues:
            print(f'No price on {par}')
            price = None
        elif has_price:
            price = has_price.group(1)
        else:
            price = None
        if not has_kind and verbose and par not in seen_issues:
            print(f'No kind on {par}')
            kind = None
        elif has_kind:
            kind = has_kind.group(1)
        else:
            kind = None
        if not has_vol and verbose and par not in seen_issues:
            print(f'No volume on {par}')
            vol = None
        elif has_vol:
            vol = has_vol.group(1)
        else:
            vol = None

        if (not has_price) or (has_kind) or (has_vol):
            seen_issues.append(par)

        return {'size'  : vol,
                'kind'  : kind,
                'price' : price}
    else:
        return None

def parse_beer_text(beer):
    paragraphs = [e.text for e in beer.find_elements_by_xpath('''.//p''')]

    par_1 = list(filter(None, get_par_type_1(paragraphs)))
    par_3 = list(filter(None, get_par_type_3(paragraphs)))

    # Handle too many or too few values
    if par_1:
        par_1 = par_1[0]
    else:
        par_1 = {}

    if par_3:
        par_3 = sorted(par_3, key = len, reverse = True)[0]
    else:
        par_3 = {}


    return dict(**par_1, **par_3)




################################################################################
#
# Part 4 : Additional parser for the bar information
#
################################################################################

def parse_bar_info(soup, **kwargs):

    header = soup.select('div:has(> h1)')[0]
    bar_name = header.select('h1')[0].text.strip()

    subheader = header.select('p')[0].text
    subheader = subheader.replace('\n', ' ')
    clean_subhead = ' '.join(filter(None, map(lambda s : s.strip(), subheader.split(' '))))

    nyc_neighborhood = '([^,]*), ((?:[^,]*), NY)'
    city             = '((?:[^,]*), [A-Z][A-Z])'
    word             = '[a-zA-Z]+'
    rest_type        = f'({word} {word}|{word})'

    keys = ['establishment_type', 'neighborhood', 'city']
    formats = [
        (f'{rest_type} in {nyc_neighborhood}'  ,  keys              ),
        (f'{rest_type} in {city}'              ,  [keys[0], keys[2]]),
        (f'in {nyc_neighborhood}'              ,  keys[1:]          ),
        (f'in {city}'                          ,  keys[2:]          ),
        (f'{rest_type}'                        ,  keys[:1]           )
    ]

    if '\n' in clean_subhead:
        breakpoint()

    out_dict = {}
    for format_, fields in formats:
        re_ =  re.search(format_, clean_subhead)
        if re_:
            out_dict = dict(zip(fields, re_.groups()))
            break

    if not out_dict:
        print(f'No parse on {header.text}')

    for key in keys:
        if key not in out_dict:
            out_dict[key] = None

    out_dict['bar_name'] = bar_name
    out_dict['bar_url'] = kwargs['url']

    return pd.DataFrame.from_records([out_dict])
