from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time

# Заголовок экрана SMS (RU / EN)
_SMS_TITLE_XPATH = "//h1//span[contains(., 'Введите код из') or contains(., 'Enter SMS code')]"
_SMS_CHECK_XPATH = "//h1//span[contains(., 'Введите код из') or contains(., 'Enter SMS code')]"


def click_password_method(driver, timeout=5):
    """
    Ищет кнопку/элемент «Пароль» в поп-апе подтверждения несколькими XPath/по тексту.
    Возвращает True если клик прошёл, иначе False.
    """
    selectors = [
        "//button[.//*[normalize-space(.)='Пароль'] or normalize-space(.)='Пароль']",
        "//span[normalize-space(.)='Пароль']/ancestor::button[1]",
        "//span[normalize-space(.)='Пароль']/ancestor::*[@role='button'][1]",
        "//span[normalize-space(.)='Пароль']/ancestor::*[contains(@class, 'vkuiClickable__realClickable')][1]",
        "//span[normalize-space(.)='Пароль']/ancestor::*[contains(@class, 'vkuiTappable__host')][1]",
        (
            "//*[normalize-space(.)='Пароль']/ancestor::*[self::button or @role='button' "
            "or contains(@class, 'vkuiClickable__realClickable') or contains(@class, 'vkuiTappable__host')][1]"
        ),
        "//div[contains(normalize-space(.), 'Пароль')]",
        "//button[span[contains(text(), 'Пароль')]]",
        "//span[contains(text(), 'Пароль')]/ancestor::div[1]",
    ]

    for xpath in selectors:
        try:
            elem = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            print(f"[+] Найдена кнопка 'Пароль' по селектору: {xpath}")
            try:
                elem.click()
            except Exception:
                driver.execute_script("arguments[0].click();", elem)
            print("[+] Клик по кнопке 'Пароль' выполнен")
            return True
        except TimeoutException:
            continue
        except NoSuchElementException:
            continue
        except Exception as e:
            print(f"[!] Ошибка на селекторе {xpath}: {e}")
            continue

    print("[!] Кнопка 'Пароль' не найдена ни по одному варианту")
    return False


def close_popup_if_exists(driver, timeout=3):
    """
    Проверяет поп-ап с кнопкой «Закрыть» и закрывает, если есть.
    """
    close_selectors = [
        "/html/body/div/div/div/div/div/div[1]/div[2]/div/div[2]/div/div[3]/button",
        "//button[contains(normalize-space(.), 'Закрыть')]",
        "//button[contains(normalize-space(.), 'Close')]",
        "//button[@aria-label='Закрыть']",
        "//button[@aria-label='Close']",
        "//button[contains(@class, 'close')]",
        "//div[contains(@class, 'close')]",
        "//span[contains(@class, 'close')]",
        "//button[contains(text(), '×')]",
        "//span[contains(text(), '×')]",
    ]

    for xpath in close_selectors:
        try:
            elem = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )

            if elem.is_displayed():
                print(f"[+] Найден поп-ап с кнопкой закрытия: {xpath}")
                try:
                    elem.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", elem)

                print("[+] Поп-ап закрыт")
                return True

        except (TimeoutException, NoSuchElementException):
            continue
        except Exception as e:
            if "timeout" not in str(e).lower():
                print(f"[!] Ошибка при закрытии поп-апа: {e}")
            continue

    return False


def handle_sms_confirmation_window(driver, log_signal=None, wait_time=10):
    """
    Обрабатывает окно «Введите код из SMS»: нажимает «Подтвердить другим способом».
    """
    try:
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.XPATH, _SMS_TITLE_XPATH))
        )
        print("[*] SMS Обнаружено окно ввода кода из SMS")

        if log_signal:
            log_signal.emit("[*] SMS Обнаружено окно ввода кода из SMS")

        close_popup_if_exists(driver)

        other_method_button = WebDriverWait(driver, wait_time).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test-id='other-verification-methods']"))
        )

        print("[*] SMS Найдена кнопка 'Подтвердить другим способом'")

        if log_signal:
            log_signal.emit("[*] SMS Найдена кнопка 'Подтвердить другим способом'")
        other_method_button.click()
        print("[*] SMS Нажата кнопка 'Подтвердить другим способом'")

        if log_signal:
            log_signal.emit("[*] SMS Нажата кнопка 'Подтвердить другим способом'")
        time.sleep(2)
        click_password_method(driver)

        time.sleep(2)
        return True

    except TimeoutException:
        print("[*] SMS Окно SMS неподтверждения или кнопка не найдены")
        return False
    except Exception as e:
        print(f"[*] SMS Ошибка при обработке окна SMS: {e}")
        return False


def check_for_sms_window(driver, log_signal=None):
    """
    Проверяет наличие окна ввода кода из SMS без ожидания.
    """
    try:
        print("[*] Проверяем SMS")
        if log_signal:
            log_signal.emit("[*] Проверяем SMS")
        driver.find_element(By.XPATH, _SMS_CHECK_XPATH)
        handle_sms_confirmation_window(driver, log_signal)
        return True
    except NoSuchElementException:
        return False
