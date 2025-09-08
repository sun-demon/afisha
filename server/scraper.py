from typing import Optional
import json
import time
import glob
import os

from playwright.sync_api import sync_playwright

from logging_utils import get_scraper_logger, setup_logging


logger = get_scraper_logger()
city='moscow'
rubric_url_prefix = f'https://afisha.yandex.ru/{city}?rubric='
rubrics = 'cinema concert theatre kids art sport standup excursions show quests'.split()
data_test_id_str = 'data-test-id'
data_dirname = 'data'


def create_data_test_id_selector(id: str) -> str:
    return f'[{data_test_id_str}="{id}"]'


def create_events_filename(unique_name_part: str) -> str:
    return f'{data_dirname}/{city}_events{unique_name_part}.json'


def scrape_events() -> Optional[list]:
    events = dict()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            context.set_default_timeout(5 * 60 * 1000) # 5 minutes
            rubric_page = context.new_page()

            logger.info('Start scraping moscow event rubrics.')

            for i, rubric in enumerate(rubrics, 1):
                rubric_url = rubric_url_prefix + rubric
                rubric_page.goto(rubric_url)
                
                event_list_selector = create_data_test_id_selector('mainPage.eventsList.list')
                rubric_page.wait_for_selector(event_list_selector)
                events_list_tag = rubric_page.query_selector(event_list_selector)

                if not events_list_tag:
                    raise RuntimeError(f'not found main page event list selector: {event_list_selector}')

                events_more_selector = create_data_test_id_selector('mainPage.rubricContent.eventsListMore')
                for _ in range(20):
                    rubric_page.press('body', 'PageDown')
                    rubric_page.wait_for_selector(f'{events_more_selector}:not(:has(>span)), {event_list_selector}:not(:has(>{events_more_selector}))')
                    more_events_button = rubric_page.query_selector(events_more_selector)
                    if more_events_button != None:
                        more_events_button.click()
                    else:
                        break

                event_selector = create_data_test_id_selector('eventCard.root')
                event_tags = rubric_page.query_selector_all(event_selector)
                
                for event_tag in event_tags:
                    id = event_tag.get_attribute('data-event-id')

                    if id in events:
                        if rubric not in events[id]['rubrics']:
                            events[id]['rubrics'].append(rubric)
                        continue

                    title_selector = create_data_test_id_selector('eventCard.eventInfoTitle')
                    event_tag.wait_for_selector(title_selector, state='hidden')
                    title = event_tag.query_selector(title_selector).inner_text()
                    
                    image_tag = event_tag.query_selector('img')
                    image_url = image_tag.get_attribute('src') if image_tag else None
                    
                    rating_tag = event_tag.query_selector(create_data_test_id_selector('event-card-rating'))
                    rating = rating_tag.inner_text() if rating_tag else None

                    price_tag = event_tag.query_selector(create_data_test_id_selector('event-card-price'))
                    price = price_tag.inner_text() if price_tag else None

                    detail_selector = create_data_test_id_selector('eventCard.eventInfoDetails') + ' li'
                    event_tag.wait_for_selector(detail_selector)
                    details = ' • '.join(map(lambda tag: tag.inner_text(), event_tag.query_selector_all(detail_selector)))

                    # link_selector = create_data_test_id_selector('eventCard.link')
                    # event_tag.wait_for_selector(link_selector)
                    # link_suffix = event_tag.query_selector(link_selector).get_attribute('href').split('?')[0]

                    events[id] = {
                        'title': title,
                        'image_url': image_url,
                        'rating': rating,
                        'price': price,
                        'details': details,
                        
                        'rubrics': [rubric]
                    }                      

                
                logger.info(f'Scanned {i}/{len(rubrics)} rubric "{rubric}": found {len(event_tags)} events.')

            browser.close()

        logger.info('Stop scraping.')
        return events
    except TimeoutError as e:
        logger.error(f'The file must be started manually!!! Not in CLI mode without GUI, because Afisha.Yandex check bot work! Error info: {e}')
        return None
    except Exception as e:
        logger.error(f'Extreme stop scraping. Error info: {e}')
        raise e


def get_last_events() -> Optional[dict]:
    events_data_all_filenames_pattern = create_events_filename('*')
    events_filename = max(glob.glob(events_data_all_filenames_pattern))
    events = dict()
    with open(events_filename, encoding='UTF-8') as f:
        events = json.loads(f.read())
    return events


def save_events(events: dict):
    events_json_str = json.dumps(events, ensure_ascii=False, indent=4)
    timestr = time.strftime(f'%Y.%m.%d_%H.%M.%S')
    events_data_filename = create_events_filename(f'_{timestr}')
    os.makedirs(data_dirname, exist_ok=True)
    with open(events_data_filename, 'w', encoding='UTF-8') as f:
        f.write(events_json_str)
    logger.info(f'Saved events to {events_data_filename} file.')


if __name__ == '__main__':
    setup_logging()
    
    moscow_events = scrape_events() 
    # or events = get_last_events() if you have data/moscow_events{...}.json files
    
    # you can skip this down part code if you wouldn't save new moscow_events_{yyyy.mm.dd_HH.MM.SS}.json file
    save_events(moscow_events)
