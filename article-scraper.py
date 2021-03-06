# -*- coding: utf-8 -*-

## Import necessary libraries...
from newspaper import Article
from selenium import webdriver
from bs4 import BeautifulSoup
from time import sleep
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import csv
import math
import datetime
import requests
import os
import easygui_qt as qt
import unicodedata
import sys

## GUI - Prompt user for a search topic...
input_topic = qt.get_string('Enter a search topic: ', title = 'Article Scraper')

## Convert input topic to lowercase
topic = (input_topic.lower()).replace(' ', '%20')

## GUI - Prompt user for a start and end dates...
input_date_start = qt.get_date('Select search START date')
input_date_end = qt.get_date('Select search END date')

## Convert format of date variables...
start = datetime.datetime.strptime(input_date_start, '%a %b %d %Y')
end = datetime.datetime.strptime(input_date_end, '%a %b %d %Y')

## Date range string to be used as folder title...
daterange = start.strftime("%m%d%Y")+'_to_'+end.strftime("%m%d%Y")

## GUI - Prompt user to select news sources...
choices = ['Washington Post', 'Reuters']
journal = qt.get_list_of_choices(title='Select Journals to Scrape',
                                choices=choices)

## GUI - Prompt user to select path for output...
savepath = qt.get_directory_name(title='Select output location...')


## Configure PhantomJS browser to accept JavaScript Clicks...
user_agent = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) " +
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.57 Safari/537.36"
)
dcap = dict(DesiredCapabilities.PHANTOMJS)
dcap["phantomjs.page.settings.userAgent"] = user_agent

## Create PhantomJS browser session....
browser = webdriver.PhantomJS(desired_capabilities=dcap)
browser.set_window_size(1024, 768)

## Function for scraping URLs from The Washington Post's website...
def wapo():

    ## Base URL for our searches
    baseUrl = 'https://www.washingtonpost.com/newssearch/?query=%s&sort=Date' % (topic)

    ## Visit website and 'create the soup' of html to explore
    browser.get(baseUrl)
    content = browser.page_source
    soup = BeautifulSoup(content, 'html.parser')

    ## Find the span that has the search result counter and extract that number
    spans = soup.find_all('span', class_='pb-search-number')

    for span in spans:
        span_string = str(span)
        if 'results.total' in span_string:
            result_counter = span.getText()

    search_results = float(result_counter[1:-1])
    
    ## Ask the user if they would like to continue the download process
    warning_title_wp = 'There are %s total articles available in The Washington Post for this topic.\n\nPlease ensure you have a stable Internet connection.\n\nWould you like to continue?' % (str(int(search_results)))
    warning_wp = qt.get_continue_or_cancel(warning_title_wp)

    if (warning_wp == "continue"):

        ## Calculate the amount of pages to search through
        ## ----
        page_count = int(math.ceil(search_results / 10))

        ## Notify user of search result total
        ## ----
        print 'There are ' + str(search_results) + ' results for ' + input_topic

        ## Prepare counters and list to be used in upcoming loops
        ## ----
        counter = 0
        wapo_results_list = []

        ## Create a CSV file with all URLs and publish dates (DATE SAVED TO LOOK INTO SEARCH CAPABILITIES) 
        ## Create a list with all URLs to be used by the Newspaper library
        ## ----

        while (page_count >= 1):

            page_content = browser.page_source
            new_soup = BeautifulSoup(page_content, 'html.parser')
            results = new_soup.find_all('div', class_='pb-feed-item ng-scope')

            for result in results:
                timestamp = result.find('span', class_='pb-timestamp ng-binding').getText()
                
                if timestamp:
                    date = datetime.datetime.strptime(timestamp, '%b %d, %Y')
                
                wapo_url = result.find('a')['href']
                counter += 1
                
                if start <= date <= end:
                    print '#' + str(counter) + ' ...Retrieving search result from ' + str(date)               
                    wapo_results_list.append(wapo_url)

            if date < start:
                break

            browser.find_element_by_class_name('next').click()

            sleep(1)
            page_count -= 1
    else:
        browser.quit()
        sys.exit()

    return wapo_results_list


## Function for scraping URLs from Reuters's website...
def reuters():

    baseUrl = 'http://www.reuters.com/search/news?blob=%s&sortBy=date' % (topic)

    ## Visit website
    ## ----
    browser.get(baseUrl)

    page = 0
    count = 0

    content = browser.page_source
    soup = BeautifulSoup(content, 'html.parser')

    search_results = soup.find('span', class_='search-result-count-num').getText()
    search_results = search_results.replace(',', '')


    ## Ask the user if they would like to continue the download process
    warning_title_r = 'There are %s total articles available in Reuters for this topic.\n\nPlease ensure you have a stable Internet connection.\n\nWould you like to continue?' % (str(int(search_results)))
    warning_r = qt.get_continue_or_cancel(warning_title_r)

    if (warning_r == "continue"):

        number_of_clicks = int(search_results) / 10

        while page < number_of_clicks:

            browser.find_element_by_class_name('search-result-more-txt').click();
            page += 1
            print 'Getting URLs from page' + str(page)
            sleep(1)

        content = browser.page_source
        soup = BeautifulSoup(content, 'html.parser')

        results = soup.find_all('div', class_='search-result-content')
        reu_results_list = []

        # Create a CSV with various data fields for each article, 
        # then put article into a text file
        # ----
        for result in results:

            title = result.find('h3', class_='search-result-title').getText()
            reu_url = result.find('a')['href']
            timestamp = result.find('h5', class_='search-result-timestamp').getText()
            timestamp = timestamp[:-12]
            
            if timestamp:
                date = datetime.datetime.strptime(timestamp, '%B %d, %Y')
            
            count += 1

            if start <= date <= end:
                print '#' + str(count) + ' ...Retrieving search result from ' + str(date)                       
                reu_results_list.append('http://www.reuters.com/'+reu_url)

    else:
        browser.quit()
        sys.exit()

    return reu_results_list

## Function for writing news article text files and metadata spreadsheet...
def write_csv(results_file_name, results_path, list_of_urls):

    ## Create a directory for all articles if it doesn't exist
    ## ----
    path = savepath+'/ArticleScraper_Output/'+input_topic+'/'+results_path+'/'+daterange

    if not os.path.exists(path):
        os.makedirs(path)

    ## Create a CSV with various data fields for each article, 
    ## then put article into a text file
    ## ----

    counter2 = 0

    csv_file = path+'/'+results_file_name + '.csv'

    with open(csv_file, 'w') as csvfile:
        fieldnames = ['id','date','search term','title','authors','URL','filepath']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for url in list_of_urls:

            a = Article(url)
            a.download()
            a.parse()

            title = a.title
            title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore')

            text = a.text
            text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore')

            publish_date = a.publish_date
            # publish_date = unicodedata.normalize('NFKD', publish_date).encode('ascii', 'ignore')

            authors = a.authors
            # authors = unicodedata.normalize('NFKD', authors).encode('ascii', 'ignore')


            counter2 += 1
            article_id = 'article'+str(counter2)
            
            filename = article_id+'.txt'
            filepath = os.path.join(path, filename)

            print 'writing %s' % (article_id)
            writer.writerow({'id': article_id,'date': publish_date, 'search term': input_topic, 'title': title, 'authors': authors, 'URL': url, 'filepath': filepath})

            file = open(filepath,'w')

            file.write(title)
            file.write('\n\n')
            file.write(text)
            
            file.close()


#######
# Switch for selecting news source. Technical debt: only selecting all, 
# or one source at a time works correctly. Must account for other combinations

if (all (x in journal for x in ['Washington Post', 'Reuters'])):
    
    print 'Searching Washington Post for ' + input_topic
    wp_url_list = wapo()
    write_csv('wapo_results', 'wapo_articles/', wp_url_list)

    print 'Searching Reuters for ' + input_topic
    r_url_list = reuters()
    write_csv('reuters_results', 'reuters_articles/', r_url_list) 

    ## Close browser session
    browser.quit()


elif ('Washington Post' in journal):

    print 'Searching Washington Post for ' + input_topic
    url_list = wapo()
    write_csv('wapo_results', 'wapo_articles/', url_list)

    ## Close browser session
    browser.quit()

elif ('Reuters' in journal):

    print 'Searching Reuters for ' + input_topic
    url_list = reuters()
    write_csv('reuters_results', 'reuters_articles/', url_list)

    ## Close browser session
    browser.quit()



sys.exit()

