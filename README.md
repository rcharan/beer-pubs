# The New York Craft Beer Scene

We analyze the beer menus listed by ~200 New York City craft beer bars (~7500)
beers listed.
- We find statistically significant differences in taste in the four
boroughs where we collected sufficient data (Staten Island, Brooklyn, Manhattan,
and Queens).
- We estimated the price per ounce of *alcohol* (not ounce of beer)
of $10. Finally, we find
- We find a statistically significant difference in prices based on the origin
of the beer, with foreign beers most expensive, followed by beers outside New York
state, and finally beers made in New York City or New York state statistically tied.

## Contributors
- Dave Bletsch ([github](https://github.com/davebletsch))
- Ravi Charan ([github](https://github.com/rcharan/))

## Background
This is our second Flatiron School (NYC Data Science), for module 3

See the presentation and conclusions on [Google Slides](https://docs.google.com/presentation/d/1MCm-oAfYUBigihPCMhawgKsBIC7iVu3WU9zfzCGGvuE/edit?usp=sharing) or view the pdf in our repository.

## Data
We scraped beer menus from [beermenus.com](http://beermenus.com/) using a
combination of Selenium, Requests, and BeautifulSoup. You can find the cleaned
data in a csv in our repsoitory


## How to use this Repo
- The main analysis is in analysis.ipynb.
- You can find our presentation in the presentation directory.
- You can find our code to perform the webscraping in the scrape directory. Note:
scraping can take several hours and you can expect data to vary as bars regularly update their menus.
- You can find our data cleaning in the datacleaning directory
