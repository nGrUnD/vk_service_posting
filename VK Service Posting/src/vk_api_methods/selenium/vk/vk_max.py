import time

from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def click_password_method(driver, timeout=5):
    """
    Ищет кнопку/элемент 'Пароль' в поп-апе подтверждения несколькими XPath/по тексту.
    Возвращает True если клик прошёл, иначе False.
    """
    selectors = [
        # ваши полные XPath
        "/html/body/div/div/div/div/div/div[1]/div[2]/div[2]/div/div[1]/div[2]/div/div[4]", # MAX
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


def handle_max_confirmation_window(driver, log_signal = None, wait_time=10):
    """
    Обрабатывает окно подтверждения в мессенджере MAX
    Ищет и нажимает кнопку "Подтвердить другим способом"
    """
    try:
        # Ждем появления текста "Подтвердите вход в мессенджере MAX"
        max_text = WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located(
                (By.XPATH, "//span[contains(text(), 'Подтвердите вход в') and contains(text(), 'MAX')]")
            )
        )
        if log_signal:
            log_signal.emit("[*] MAX Обнаружено окно подтверждения в мессенджере MAX")
        print("[*] MAX Обнаружено окно подтверждения в мессенджере MAX")

        # Ищем кнопку "Подтвердить другим способом" по data-test-id
        other_method_button = WebDriverWait(driver, wait_time).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test-id='other-verification-methods']"))
        )

        if log_signal:
            log_signal.emit("[*] MAX Найдена кнопка 'Подтвердить другим способом'")
        print("[*] MAX Найдена кнопка 'Подтвердить другим способом'")

        # Нажимаем кнопку
        other_method_button.click()
        if log_signal:
            log_signal.emit("[*] MAX Нажата кнопка 'Подтвердить другим способом'")
        print("[*] MAX Нажата кнопка 'Подтвердить другим способом'")

        # Небольшая пауза для загрузки следующего окна
        time.sleep(2)
        click_password_method(driver)

        return True

    except TimeoutException:
        print("[*] MAX Окно подтверждения в мессенджере MAX не найдено или кнопка недоступна")
        return False
    except Exception as e:
        print(f"[*] MAX Ошибка при обработке окна MAX: {e}")
        return False


def check_for_max_window(driver, log_signal = None):
    """
    Проверяет наличие окна подтверждения MAX без ожидания
    """
    try:
        print("[*] Проверяем MAX")
        if log_signal:
            log_signal.emit("[*] Проверяем MAX")
        # Проверяем наличие характерного текста
        driver.find_element(
            By.XPATH, "//span[contains(text(), 'Подтвердите вход в') and contains(text(), 'MAX')]"
        )
        handle_max_confirmation_window(driver,log_signal)
        return True
    except NoSuchElementException:
        return False