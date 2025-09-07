from typing import Optional
import json
import time
import glob

from playwright.sync_api import sync_playwright

from scripts.logging_utils import get_scraper_logger


logger = get_scraper_logger()


yandex_afisha_base_url = 'https://afisha.yandex.ru'
yandex_afisha_movie_ganres = 'action detective drama comedy romance adventure tragicomedy thriller horror fiction cartoon sport-movie dokumentalniy art_film family_movie'.split()
yandex_afisha_data_test_id_attribute_name = 'data-test-id'


def __create_data_test_id_selector(data_test_id: str) -> str:
    return f'[{yandex_afisha_data_test_id_attribute_name}="{data_test_id}"]'


def __create_data_moscow_movies_filename(unique_name_part: str) -> str:
    return f'data/moscow_movies{unique_name_part}.json'


def scrape_yandex_afisha_moscow_movies() -> Optional[dict]:
    city = 'moscow'
    event_type = 'cinema'

    city_event_type_url = f'{yandex_afisha_base_url}/{city}/{event_type}'

    moscow_movies = dict()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            
            page = browser.new_page()
            for i, movie_ganre in enumerate(yandex_afisha_movie_ganres):
                logger.info(f'start scanning {i + 1}/{len(yandex_afisha_movie_ganres)} movie ganre')
                moscow_movie_ganre_url = f'{city_event_type_url}/?filter={movie_ganre}'
                logger.info(f'scraping URL: {moscow_movie_ganre_url}')
                page.goto(moscow_movie_ganre_url)

                events_list_selector = __create_data_test_id_selector('rubricPage.eventsList.list')
                page.wait_for_selector(events_list_selector)
                events_list = page.query_selector(events_list_selector)
                if not events_list:
                    raise RuntimeError(f'not found main events list div by selector: {events_list_selector}')

                get_more_events_button_selector = __create_data_test_id_selector('rubricPage.rubricContent.eventsListMore')
                while True:
                    page.press('body', 'PageDown')
                    page.wait_for_selector(f'{get_more_events_button_selector}:not(:has(>span)), {events_list_selector}:not(:has(>{get_more_events_button_selector}))')
                    get_more_events_button = page.query_selector(get_more_events_button_selector)
                    if get_more_events_button != None:
                        get_more_events_button.click()
                    else:
                        break

                event_card_selector = '[data-component="EventCard"]'
                event_card_list = page.query_selector_all(event_card_selector)
                
                previous_moscow_movies_lenght = len(moscow_movies) # for checking new events count
                for event_card in event_card_list:
                    event_id = event_card.get_attribute('data-event-id')
                    if event_id not in moscow_movies:
                        event_title_selector = __create_data_test_id_selector('eventCard.eventInfoTitle')
                        
                        event_card.wait_for_selector(event_title_selector)
                        event_title = event_card.query_selector(event_title_selector).inner_text()

                        event_link_selector = __create_data_test_id_selector('eventCard.link')
                        event_card.wait_for_selector(event_link_selector, state='hidden')
                        event_link = event_card.query_selector(event_link_selector).get_attribute('href')
                        event_link_part = event_link.rsplit('/', 1)[-1].split('?', 1)[0]
                        
                        event_avatar_element = event_card.query_selector('img')
                        event_avatar_url = event_avatar_element.get_attribute('src') if event_avatar_element else None
                        
                        event_rating_element = event_card.query_selector(__create_data_test_id_selector('event-card-rating'))
                        event_rating = event_rating_element.inner_text() if event_rating_element else None

                        event_price_element = event_card.query_selector(__create_data_test_id_selector('event-card-price'))
                        event_price = event_price_element.inner_text() if event_price_element else None
                        if event_price in ['Есть билеты', 'Нет билетов']:
                            event_price = None

                        event_details_selectors = __create_data_test_id_selector('eventCard.eventInfoDetails') + ' li'
                        event_card.wait_for_selector(event_details_selectors)
                        event_details = ' • '.join(map(lambda element: element.inner_text(), event_card.query_selector_all(event_details_selectors)))


                        moscow_movies[event_id] = {
                            'title': event_title,
                            'link': event_link_part,
                            'avatar': event_avatar_url,
                            'rating': event_rating,
                            'price': event_price,
                            'details': event_details
                        }

                new_unique_movies_ids_number = len(moscow_movies) - previous_moscow_movies_lenght
                logger.info(f'end scanning {i + 1}/{len(yandex_afisha_movie_ganres)} movie ganre: found {len(event_card_list)} movie cards, of which {new_unique_movies_ids_number} are new unique')

            browser.close()

        return moscow_movies
    except TimeoutError as e:
        logger.error(f'The file must be started manually!!! Not in CLI mode without GUI, because Afisha.Yandex check bot work! Error info: {e}')
        return None


def get_last_moscow_movies() -> Optional[dict]:
    moscow_movies_data_all_filenames_pattern = __create_data_moscow_movies_filename('*')
    moscow_movies_filename = max(glob.glob(moscow_movies_data_all_filenames_pattern))
    moscow_movies = dict()
    with open(moscow_movies_filename, encoding='UTF-8') as f:
        moscow_movies = json.loads(f.read())
    return moscow_movies


def save_moscow_movies_data(moscow_movies: dict):
    moscow_movies_json_str = json.dumps(moscow_movies, ensure_ascii=False, indent=4)
    timestr = time.strftime(f'%Y.%m.%d_%H.%M.%S')
    moscow_movies_data_filename = __create_data_moscow_movies_filename(f'_{timestr}')
    with open(moscow_movies_data_filename, 'w', encoding='UTF-8') as f:
        f.write(moscow_movies_json_str)
