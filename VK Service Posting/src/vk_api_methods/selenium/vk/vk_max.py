import re
import time

from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Текст экрана MAX (RU / EN)
_MAX_SCREEN_XPATH = (
    "//span[(contains(., 'Подтвердите вход') and contains(., 'MAX'))"
    " or (contains(., 'Confirm sign-in') and contains(., 'MAX'))]"
)


def wait_for_active_other_method_button(driver, selectors, timeout=45):
    """
    Ждёт, пока кнопка «Другие способы подтверждения» станет реально активной.
    На MAX экран может показываться таймер 00:30, хотя Selenium уже считает кнопку кликабельной.
    """
    timer_pattern = re.compile(r"\b\d{1,2}:\d{2}\b")

    def active_button(_driver):
        try:
            body_text = _driver.find_element(By.TAG_NAME, "body").text or ""
            if timer_pattern.search(body_text):
                return False
        except NoSuchElementException:
            return False

        for by, selector in selectors:
            try:
                button = _driver.find_element(by, selector)
            except NoSuchElementException:
                continue

            text = (button.text or "").strip()
            class_name = button.get_attribute("class") or ""
            is_disabled = (
                button.get_attribute("disabled") is not None
                or button.get_attribute("aria-disabled") == "true"
                or button.get_attribute("data-disabled") == "true"
                or "disabled" in class_name.lower()
            )

            if (
                button.is_displayed()
                and button.is_enabled()
                and not is_disabled
                and not timer_pattern.search(text)
            ):
                return button

        return False

    return WebDriverWait(driver, timeout).until(active_button)


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
    ]

    for xpath in selectors:
        try:
            elem = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            elem_text = (elem.text or "").strip()
            if "Пароль" not in elem_text or "SMS" in elem_text or "СМС" in elem_text:
                print(f"[!] Пропущен неподходящий элемент для 'Пароль': {elem_text}")
                continue

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


def handle_max_confirmation_window(driver, log_signal=None, wait_time=10):
    """
    Обрабатывает окно подтверждения в мессенджере MAX:
    ищет и нажимает «Подтвердить другим способом» (после ожидания таймера, если есть).
    """
    try:
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.XPATH, _MAX_SCREEN_XPATH))
        )
        if log_signal:
            log_signal.emit("[*] MAX Обнаружено окно подтверждения в мессенджере MAX")
        print("[*] MAX Обнаружено окно подтверждения в мессенджере MAX")

        other_method_selectors = [
            (By.CSS_SELECTOR, "button[data-test-id='other-verification-methods']"),
            (By.CSS_SELECTOR, "button.vkc__MaxVerificationScreen-style-module__timerButton"),
            (By.XPATH, "//button[.//span[contains(normalize-space(.), 'Другие способы подтверждения')]]"),
            (By.XPATH, "//span[contains(normalize-space(.), 'Другие способы подтверждения')]/ancestor::button[1]"),
            (By.XPATH, "/html/body/div/div/div/div/div/div[1]/div/div/div/div/div/button"),
        ]

        if log_signal:
            log_signal.emit("[*] MAX Ждём, пока закончится таймер кнопки 'Подтвердить другим способом'")
        print("[*] MAX Ждём, пока закончится таймер кнопки 'Подтвердить другим способом'")

        other_method_button = wait_for_active_other_method_button(driver, other_method_selectors, timeout=45)

        if log_signal:
            log_signal.emit("[*] MAX Найдена кнопка 'Подтвердить другим способом'")
        print("[*] MAX Найдена кнопка 'Подтвердить другим способом'")

        try:
            other_method_button.click()
        except Exception:
            driver.execute_script("arguments[0].click();", other_method_button)
        if log_signal:
            log_signal.emit("[*] MAX Нажата кнопка 'Подтвердить другим способом'")
        print("[*] MAX Нажата кнопка 'Подтвердить другим способом'")

        time.sleep(2)
        if not click_password_method(driver):
            return False

        return True

    except TimeoutException:
        print("[*] MAX Окно подтверждения в мессенджере MAX не найдено или кнопка недоступна")
        return False
    except Exception as e:
        print(f"[*] MAX Ошибка при обработке окна MAX: {e}")
        return False


def check_for_max_window(driver, log_signal=None):
    """
    Проверяет наличие окна подтверждения MAX без долгого ожидания.
    """
    try:
        print("[*] Проверяем MAX")
        if log_signal:
            log_signal.emit("[*] Проверяем MAX")
        driver.find_element(By.XPATH, _MAX_SCREEN_XPATH)
        handle_max_confirmation_window(driver, log_signal)
        return True
    except NoSuchElementException:
        return False
