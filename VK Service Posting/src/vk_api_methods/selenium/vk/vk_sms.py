from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time

def click_password_method(driver, timeout=5):
    """
    Ищет кнопку/элемент 'Пароль' в поп-апе подтверждения несколькими XPath/по тексту.
    Возвращает True если клик прошёл, иначе False.
    """
    selectors = [
        # ваши полные XPath
        "/html/body/div/div/div/div/div/div[1]/div[2]/div[2]/div/div[1]/div[2]/div/div[3]", # смс
        # более надёжные варианты по тексту
        "//div[contains(normalize-space(.), 'Пароль')]",
        "//button[span[contains(text(), 'Пароль')]]",
        "//span[contains(text(), 'Пароль')]/ancestor::div[1]"
    ]

    for xpath in selectors:
        try:
            elem = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            print(f"[+] Найдена кнопка 'Пароль' по селектору: {xpath}")
            try:
                elem.click()
            except:
                # запасной вариант если перекрыта
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
    Проверяет наличие поп-апа с кнопкой 'Закрыть' и закрывает его если есть.
    Используется для закрытия мешающих поп-апов перед основными действиями.

    Args:
        driver: Selenium WebDriver
        timeout: int - таймаут ожидания (короткий, т.к. поп-ап либо есть либо нет)

    Returns:
        True если поп-ап закрыт, False если поп-апа не было
    """
    close_selectors = [
        # ваш XPath для кнопки "Закрыть"
        "/html/body/div/div/div/div/div/div[1]/div[2]/div/div[2]/div/div[3]/button",

        # дополнительные варианты кнопок закрытия
        "//button[contains(normalize-space(.), 'Закрыть')]",
        "//button[contains(normalize-space(.), 'Close')]",
        "//button[@aria-label='Закрыть']",
        "//button[@aria-label='Close']",

        # крестики для закрытия
        "//button[contains(@class, 'close')]",
        "//div[contains(@class, 'close')]",
        "//span[contains(@class, 'close')]",

        # иконки закрытия (×)
        "//button[contains(text(), '×')]",
        "//span[contains(text(), '×')]"
    ]

    for xpath in close_selectors:
        try:
            elem = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )

            # Проверяем, что элемент видимый (поп-ап может быть скрыт)
            if elem.is_displayed():
                print(f"[+] Найден поп-ап с кнопкой закрытия: {xpath}")
                try:
                    elem.click()
                except:
                    # JS клик если обычный не работает
                    driver.execute_script("arguments[0].click();", elem)

                print("[+] Поп-ап закрыт")
                return True

        except (TimeoutException, NoSuchElementException):
            continue
        except Exception as e:
            # Логируем только если это не обычный timeout
            if "timeout" not in str(e).lower():
                print(f"[!] Ошибка при закрытии поп-апа: {e}")
            continue

    # Не пишем сообщение, т.к. отсутствие поп-апа - это норма
    return False


def handle_sms_confirmation_window(driver, log_signal = None, wait_time=10):
    """
    Обрабатывает окно подтверждения по SMS:
    нажимает кнопку "Подтвердить другим способом".
    """
    try:
        # Ждём появления заголовка "Введите код из SMS"
        sms_title = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.XPATH, "//h1//span[contains(., 'Введите код из') or contains(., 'Enter SMS code')]"))
        )
        print("[*] SMS Обнаружено окно ввода кода из SMS")

        if log_signal:
            log_signal.emit("[*] SMS Обнаружено окно ввода кода из SMS")

        close_popup_if_exists(driver)

        # Ищем кнопку "Подтвердить другим способом" по data-test-id
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


def check_for_sms_window(driver, log_signal = None):
    """
    Проверяет наличие окна 'Введите код из SMS' без ожидания.
    """
    try:
        print("[*] Проверяем SMS")
        if log_signal:
            log_signal.emit("[*] Проверяем SMS")
        driver.find_element(By.XPATH, "//h1//span[contains(., 'Введите код из') or contains(., 'Enter SMS code')]")
        handle_sms_confirmation_window(driver)
        return True
    except NoSuchElementException:
        return False