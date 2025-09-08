from typing import Optional
import json
import time
import glob

from playwright.sync_api import sync_playwright

from scripts.logging_utils import get_scraper_logger


logger = get_scraper_logger()

city='moscow'
rubric_url_prefix = f'https://afisha.yandex.ru/{city}?rubric='
rubrics = 'cinema concert theatre kids art sport standup excursions show quests'.split()
data_test_id_str = 'data-test-id'


def create_data_test_id_selector(id: str) -> str:
    return f'[{data_test_id_str}="{id}"]'


def create_events_filename(unique_name_part: str) -> str:
    return f'data/{city}_events{unique_name_part}.json'


def scrape_events() -> Optional[list]:
    events = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            context.set_default_timeout(5 * 60 * 1000) # 5 minutes
            rubric_page = context.new_page()

            for i, rubric in enumerate(rubrics, 1):
                rubric_url = rubric_url_prefix + rubric
                rubric_page.goto(rubric_url)
                
                event_list_selector = create_data_test_id_selector('mainPage.eventsList.list')
                rubric_page.wait_for_selector(event_list_selector)
                events_list_tag = rubric_page.query_selector(event_list_selector)

                if not events_list_tag:
                    raise RuntimeError(f'not found main page event list selector: {event_list_selector}')

                events_more_selector = create_data_test_id_selector('mainPage.rubricContent.eventsListMore')
                for _ in range(10):
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

                    title_selector = create_data_test_id_selector('eventCard.eventInfoTitle')
                    event_tag.wait_for_selector(title_selector)
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

                    event = {
                        'id': id,

                        'title': title,
                        'image_url': image_url,
                        'rating': rating,
                        'price': price,
                        'details': details,
                        
                        'rubric': rubric
                    }                      

                
                logger.info(f'scanned {i}/{len(rubrics)} rubric "{rubric}": found {len(event_tags)} events')

            browser.close()

        return events
    except TimeoutError as e:
        logger.error(f'The file must be started manually!!! Not in CLI mode without GUI, because Afisha.Yandex check bot work! Error info: {e}')
        return None


def get_last_events() -> Optional[list]:
    events_data_all_filenames_pattern = create_events_filename('*')
    events_filename = max(glob.glob(events_data_all_filenames_pattern))
    events = []
    with open(events_filename, encoding='UTF-8') as f:
        events = json.loads(f.read())
    return events


def save_events(events: list):
    events_json_str = json.dumps(events, ensure_ascii=False, indent=4)
    timestr = time.strftime(f'%Y.%m.%d_%H.%M.%S')
    events_data_filename = create_events_filename(f'_{timestr}')
    with open(events_data_filename, 'w', encoding='UTF-8') as f:
        f.write(events_json_str)
