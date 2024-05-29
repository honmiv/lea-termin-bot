import concurrent.futures
import os
import time
from datetime import datetime

import pygame
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

mid_timeout = 90  # 90
small_timeout = 60  # 60
big_timeout = 120  # 120

termin_found = False


# returns 0 if time is found
# returns 1 if time was not found
# returns -1 if page was not reloaded
# returns -3 if session is close to the end
# returns -2 if termin not found
# returns -100 if sth happened unexpectedly
def click_next_and_check_if_time_found(driver, tab_num):
    try:
        time_text_element = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "bar"))
        )
        time_text = WebDriverWait(driver, 5).until(
            lambda _: time_text_element.text.strip()
        )
        remaining_time = datetime.strptime(time_text, "%H:%M")
        minimum_time = datetime.strptime("3:01", "%H:%M")
        if remaining_time < minimum_time:
            debug(f"{tab_num} - session is close to the end")
            return -3
    except Exception as e:
        debug(f"{tab_num} - exception while checking remaining time {e}")
        pass

    global termin_found
    if termin_found:
        debug(f"{tab_num} - Termin found in another tab. exit!")
        raise PermissionError("Termin found in another tab. exit!")
    debug(f"{tab_num} - Trying to find appointment")

    next_button = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.ID, "applicationForm:managedForm:proceed"))
    )
    next_button.click()

    try:
        WebDriverWait(driver, mid_timeout).until(EC.staleness_of(driver.find_element(By.XPATH, "//body")))
        debug(f"{tab_num} - Page with results reloaded")
        WebDriverWait(driver, mid_timeout).until(
            EC.invisibility_of_element((By.CLASS_NAME, "loading"))
        )
        debug(f"{tab_num} - Loading completed")
    except Exception as e:
        debug(f"{tab_num} - Page did not reload within {mid_timeout} seconds or the page element is not found - {e}")
        return -1

    try:
        active_tab = WebDriverWait(driver, big_timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, "antcl_active")))
        active_tab_text = active_tab.find_element(By.TAG_NAME, "span").text

        if active_tab_text == "Date selection":
            return 0
        else:
            return 1
    except Exception as e:
        debug(f"{tab_num} - Sth went wrong - {e}")
        return -100


def find_appointment(driver, tab_num):
    while True:
        driver.get("https://otv.verwalt-berlin.de/ams/TerminBuchen?lang=en")
        try:
            WebDriverWait(driver, big_timeout).until(
                EC.visibility_of_element_located((By.ID, "header"))
            )
            debug(f"{tab_num} - initial page is loaded")
            button = driver.find_element(By.XPATH, "//a[text()='Book Appointment']")
            button.click()
        except Exception as e:
            debug(f"{tab_num} - page is not loaded properly {e} - restarting")
            raise TabError("please restart driver")  # to restart driver when there is big red warning loaded
            # (otherwise when you update the page it will still stay with this warning)

        # Wait until page with agreement is loaded by checking if there is checkbox and check it
        agreement_checkbox = WebDriverWait(driver, big_timeout).until(
            EC.visibility_of_element_located((By.ID, "xi-cb-1"))
        )
        agreement_checkbox.click()

        next_button = driver.find_element(By.ID, "applicationForm:managedForm:proceed")
        next_button.click()

        # Wait until the applicant_citizenship select element is present and select value from ENV setup
        applicant_citizenship = WebDriverWait(driver, small_timeout).until(
            EC.visibility_of_element_located((By.ID, "xi-sel-400"))
        )
        debug(f"{tab_num} - form page is open")
        applicant_citizenship_select = Select(applicant_citizenship)
        time.sleep(1)
        applicant_citizenship_select.select_by_visible_text(os.getenv('APPLICANT_CITIZENSHIP_SELECT'))
        time.sleep(0.5)
        debug(f"{tab_num} - {os.getenv('APPLICANT_CITIZENSHIP_SELECT')} chosen")

        # Wait until the number_of_persons select element is present and select value from ENV setup
        number_of_persons = WebDriverWait(driver, small_timeout).until(
            EC.visibility_of_element_located((By.ID, "xi-sel-422"))
        )
        number_of_person_select = Select(number_of_persons)
        number_of_person_select.select_by_visible_text(os.getenv('NUMBER_OF_PERSONS'))
        time.sleep(0.5)
        debug(f"{tab_num} - {os.getenv('NUMBER_OF_PERSONS')} chosen")

        # Wait until the live_with_family_member select element is present and select value from ENV setup
        live_with_family_member = WebDriverWait(driver, small_timeout).until(
            EC.visibility_of_element_located((By.ID, "xi-sel-427"))
        )
        live_with_family_member_select = Select(live_with_family_member)
        live_with_family_member_select.select_by_visible_text(os.getenv('LIVE_WITH_FAMILY_MEMBER'))
        time.sleep(0.5)
        debug(f"{tab_num} - {os.getenv('LIVE_WITH_FAMILY_MEMBER')} chosen")

        if os.getenv('LIVE_WITH_FAMILY_MEMBER') == 'yes':
            # Wait until the family_member_citizenship select element is present and select value from ENV setup
            family_member_citizenship = WebDriverWait(driver, small_timeout).until(
                EC.visibility_of_element_located((By.ID, "xi-sel-428"))
            )
            family_member_citizenship_select = Select(family_member_citizenship)
            family_member_citizenship_select.select_by_visible_text(os.getenv('FAMILY_MEMBER_CITIZENSHIP'))
            debug(f"{tab_num} - {os.getenv('FAMILY_MEMBER_CITIZENSHIP')} chosen")

        # Wait until the service buttons are present and click on one from ENV setup
        WebDriverWait(driver, small_timeout).until(
            EC.visibility_of_element_located((By.ID, "xi-sel-427"))
        )

        # Find all services and click on one from ENV
        # Find all services and click on one from ENV
        div_elements = WebDriverWait(driver, small_timeout).until(
            EC.visibility_of_all_elements_located((By.CLASS_NAME, "ozg-kachel"))
        )
        for div_element in div_elements:
            label_element = div_element.find_element(By.TAG_NAME, "label")
            label_text = label_element.text.strip()
            if label_text == os.getenv('SERVICE_OPTION'):
                div_element.click()
                debug(f"{tab_num} - {os.getenv('SERVICE_OPTION')} chosen")
                break

        # Find all visa categories and click on one from ENV
        div_elements = WebDriverWait(driver, small_timeout).until(
            EC.visibility_of_all_elements_located((By.CLASS_NAME, "ozg-accordion"))
        )
        for div_element in div_elements:
            label_element = div_element.find_element(By.TAG_NAME, "label")
            label_text = label_element.text.strip()
            if label_text == os.getenv('SERVICE_CATEGORY'):
                div_element.click()
                debug(f"{tab_num} - {os.getenv('SERVICE_CATEGORY')} chosen")
                break

        # Find all visa types and click on one from ENV
        div_elements = WebDriverWait(driver, small_timeout).until(
            EC.visibility_of_all_elements_located((By.CLASS_NAME, "level3"))
        )
        for div_element in div_elements:
            label_element = div_element.find_element(By.TAG_NAME, "label")
            label_text = label_element.text.strip()
            if label_text == os.getenv('VISA_TYPE'):
                div_element.click()
                debug(f"{tab_num} - {os.getenv('VISA_TYPE')} chosen")
                break

        # wait for loading after filling all data by checking if loading screen in invisible
        WebDriverWait(driver, big_timeout).until(
            EC.invisibility_of_element((By.CLASS_NAME, "loading"))
        )

        result = 1
        while result == 1:
            result = click_next_and_check_if_time_found(driver, tab_num)

        if result < 0:
            continue

        debug(f"{tab_num} - Termin found")

        global termin_found
        if termin_found:
            debug(f"{tab_num} - Termin found in another tab. exit!")
            raise PermissionError("Termin found in another tab. exit!")
        termin_found = True

        if os.getenv('TWO_DISPLAYS').strip().lower() == 'true':
            driver.set_window_position(-2000, 150)
        driver.maximize_window()

        pygame.mixer.init()
        pygame.mixer.music.load(os.path.join(os.getcwd(), "alarm.wav"))
        pygame.mixer.music.play()

        # get all possible dates and click next possible date until there is datetime in select
        try:
            calendar = WebDriverWait(driver, big_timeout).until(
                EC.visibility_of_element_located((By.CLASS_NAME, 'ui-datepicker-inline'))
            )
            debug(f"{tab_num} - calendar found")
            clickable_dates = calendar.find_elements(By.XPATH, '//td[@data-handler="selectDay"]')

            debug(f"{tab_num} - clickable_dates found with size {len(clickable_dates)}")

            for clickable_date in clickable_dates:
                debug(f"{tab_num} - click on date {clickable_date}")
                clickable_date.click()
                debug(f"{tab_num} - date clicked")

                debug(f"{tab_num} - waiting for loading screen appeared {datetime.now()}")
                try:
                    WebDriverWait(driver, 1).until(
                        EC.visibility_of_element_located((By.CLASS_NAME, "loading"))
                    )
                except:
                    debug(f"{tab_num} - failed to wait for loading screen appeared {datetime.now()}")
                    pass
                try:
                    debug(f"{tab_num} - waiting for loading screen disappeared {datetime.now()}")
                    WebDriverWait(driver, 10).until(
                        EC.invisibility_of_element((By.CLASS_NAME, "loading"))
                    )
                    debug(f"{tab_num} - Loading completed {datetime.now()}")
                except:
                    debug(f"{tab_num} - failed to wait for loading screen disappeared {datetime.now()}")
                    pass
                # check if date selector has any date
                date_select = driver.find_element(By.ID, "xi-sel-3")
                chosen_option = date_select.find_element(By.TAG_NAME, "option")
                no_options = chosen_option.text.strip().lower() == "please select"

                if no_options:
                    debug(f"{tab_num} - date present in select menu!!!")
                    break
                else:
                    debug(f"{tab_num} - no options for selected date: {clickable_date} - go to next date")
                    continue

        except Exception as e:
            debug(f"{tab_num} - failed to find date with time {e}")
            pass

        try:
            debug(f"{tab_num} - searching checkbox_iframe")
            checkbox_iframe = WebDriverWait(driver, big_timeout).until(
                EC.presence_of_element_located((By.XPATH, '//iframe[@title="reCAPTCHA"]'))
            )
            debug(f"{tab_num} - switching to checkbox_iframe")
            driver.switch_to.frame(checkbox_iframe)
            debug(f"{tab_num} - searching for checkbox")
            checkbox = driver.find_element(By.CLASS_NAME, 'rc-anchor-content')
            debug(f"{tab_num} - clicking on checkbox")
            checkbox.click()
            debug(f"{tab_num} - switching to default content")
            driver.switch_to.default_content()
            debug(f"{tab_num} - searching for captcha iframe")
            captcha_iframe = WebDriverWait(driver, big_timeout).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//iframe[@title="recaptcha challenge expires in two minutes"]')))
            debug(f"{tab_num} - waiting captcha to be open")
            WebDriverWait(driver, big_timeout, 0.000001).until(
                lambda _: captcha_iframe.location['y'] != -9999
            )
            debug(f"{tab_num} - waiting captcha to be closed")
            WebDriverWait(driver, big_timeout, 0.000001).until(
                lambda _: captcha_iframe.location['y'] == -9999
            )
            debug(f"{tab_num} - captcha_closed - clicking next")
            next_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "applicationForm:managedForm:proceed"))
            )
            next_button.click()

        except Exception as e:
            debug(f"{tab_num} - recaptcha checkbox click failed {e}")
            pass

        debug(f"{tab_num} - sleeping 10_000")
        time.sleep(10_000)
        debug(f"{tab_num} - slept 10_000")


def find_appointment_with_retry(tab_num):
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.set_capability("unhandledPromptBehavior", "accept")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    while True:
        try:
            find_appointment(driver, tab_num)
        except TabError:
            driver.quit()
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        except PermissionError:
            driver.quit()
            break
        except Exception as e:
            debug(f"{tab_num} - sth happened. restarting: {str(e)}")
            driver.quit()
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def debug(message):
    if os.getenv('DEBUG_ENABLED').strip().lower() == 'true':
        print(message)


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.getenv('NUMBER_OF_TABS'))) as executor:
        for i in range(int(os.getenv('NUMBER_OF_TABS'))):
            executor.submit(find_appointment_with_retry, i)
