from scripts.logging_utils import setup_logging
from scrapers.yandex_afisha_moscow_events_scraper import scrape_events, get_last_events, save_events


if __name__ == '__main__':
    setup_logging()
    
    moscow_events = scrape_events() 
    # or 
    # events = get_last_moscow_movies() # if you already have any moscow_movies.json files in /data directory
    
    # you can skip this down part code if you wouldn't save new moscow_movies.json file
    save_events(moscow_events)
