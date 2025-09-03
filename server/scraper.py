from .scripts.logging_utils import setup_logging
from .scrapers.yandex_afisha_movies_scraper import scrape_yandex_afisha_moscow_movies, get_last_moscow_movies, save_moscow_movies_data


if __name__ == '__main__':
    setup_logging()
    
    moscow_movies = scrape_yandex_afisha_moscow_movies() 
    # or 
    # moscow_movies = get_last_moscow_movies() # if you already have any moscow_movies.json files in /data directory
    
    # you can skip this down part code if you wouldn't save new moscow_movies.json file
    save_moscow_movies_data(moscow_movies)
