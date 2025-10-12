import os
import random
import re
import time
import json
import base64
import gzip
import zlib
from time import sleep
import tempfile
import shutil
import zstandard as zstd

import requests
from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from seleniumwire.utils import decode

from .vk.vk_curl_build import get_vk_curl_v2
from .vk.vk_max import check_for_max_window
from .vk.vk_sms import check_for_sms_window
from src.config import settings
from ...utils.rand_user_agent import get_random_user_agent


def read_vk_public_links(file_path="public_links.txt"):
    """
    Читает ссылки на паблики VK из текстового файла.

    Args:
        file_path (str): Путь к файлу со ссылками.

    Returns:
        list: Список ссылок на паблики или пустой список, если файл не найден/ошибка.
    """
    links = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):  # Пропускаем пустые строки и комментарии
                    continue
                if line.startswith("https://vk.com/club") or line.startswith("https://vk.com/public"):
                    links.append(line)
                else:
                    print(f"[!] Неверный формат ссылки в строке {i}: {line}")
        print(f"[+] Загружено {len(links)} ссылок на паблики из {file_path}")
        return links
    except FileNotFoundError:
        print(f"[!] Файл со ссылками на паблики '{file_path}' не найден.")
        return []
    except Exception as e:
        print(f"[!] Ошибка при чтении файла со ссылками: {e}")
        return []

def read_all_credentials(file_path="account.txt"):
    """
    Читает все логины и пароли из файла

    Returns:
        list: [(login1, password1), (login2, password2), ...] или [] если ошибка
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        credentials = []
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):  # пропускаем пустые и комментарии
                continue

            if ':' not in line:
                print(f"[!] Неверный формат в строке {i}: {line}")
                continue

            login, password = line.split(':', 1)
            login, password = login.strip(), password.strip()

            if login and password:
                credentials.append((login, password))
            else:
                print(f"[!] Пустой логин или пароль в строке {i}")

        print(f"[+] Загружено {len(credentials)} аккаунтов из {file_path}")
        return credentials

    except FileNotFoundError:
        print(f"[!] Файл {file_path} не найден")
        return []
    except Exception as e:
        print(f"[!] Ошибка чтения файла: {e}")
        return []

def vk_com_to_ru(url: str) -> str:
    return url.replace('vk.com', 'vk.ru')

def press_f5(driver):
    """Нажимает F5 для обновления страницы"""
    print("[*] Нажимаем F5 для обновления страницы...")
    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.F5)
    # Альтернативный способ:
    # driver.refresh()
    time.sleep(10)  # ждём загрузки

def has_too_many_attempts_alert(driver, timeout=2):
    """
    Проверяет, есть ли окно ошибки о превышении лимита попыток:
    - Русский: 'Ошибка' / 'Слишком много попыток. Попробуйте позже.'
    - Английский: 'Ошибка' / 'Flood control: too many requests'

    Возвращает:
        True  — если окно найдено и видно
        False — если окно не найдено
    """
    try:
        wait = WebDriverWait(driver, timeout)

        # Ищем контейнер алерта
        alert = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.vkuiAlert__content"))
        )

        # Должен быть видимым
        if not alert.is_displayed():
            return False

        # Ищем заголовок и описание внутри
        title_el = alert.find_element(By.CSS_SELECTOR, ".vkuiAlert__title")
        desc_el  = alert.find_element(By.CSS_SELECTOR, ".vkuiAlert__description")

        title = (title_el.text or "").strip()
        desc  = (desc_el.text or "").strip().lower()

        # Проверяем заголовок (русский или английский)
        if title not in ["Ошибка", "Error"]:
            return False

        # Проверяем описание (русский или английский)
        if "слишком много попыток" in desc or "flood control" in desc or "too many requests" in desc:
            print("Flood control")
            return True

        return False

    except Exception:
        return False

def click_confirm_another_way_if_present(driver, timeout_each=3):
    """
    Ищет кнопку 'Подтвердить другим способом' по нескольким локаторам и кликает её, если найдена.
    Возвращает True, если нажата, иначе False.
    """
    locators = [
        # Ваш первый полный XPath
        (By.XPATH, "/html/body/div/div/div/div/div/div[1]/div/div/div/div/div/form/div[3]/button"),
        # Ваш второй полный XPath (span внутри кнопки)
        (By.XPATH, "/html/body/div/div/div/div/div/div/div/div/div/div/div/button/span"),
        # Более устойчивые варианты по тексту (лучше переживают изменения разметки)
        (By.XPATH, "//button[.//span[contains(normalize-space(.), 'Подтвердить другим способом')]]"),
        (By.XPATH, "//button[contains(normalize-space(.), 'Подтвердить другим способом')]"),
        (By.XPATH, "//span[contains(normalize-space(.), 'Подтвердить другим способом')]/ancestor::button[1]"),
    ]

    for by, selector in locators:
        try:
            btn = WebDriverWait(driver, timeout_each).until(
                EC.presence_of_element_located((by, selector))
            )
            # Если это span — поднимемся к кнопке
            if btn.tag_name.lower() == "span":
                try:
                    btn = btn.find_element(By.XPATH, "./ancestor::button[1]")
                except NoSuchElementException:
                    pass

            # Ждем кликабельность и кликаем
            btn = WebDriverWait(driver, timeout_each).until(
                EC.element_to_be_clickable((by, selector))
            )
            # На случай перекрытий или анимаций — пробуем JS click как fallback
            try:
                btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", btn)

            print("[+] Нажали 'Подтвердить другим способом'")
            return True

        except TimeoutException:
            continue
        except Exception as e:
            # Логируем и идём дальше к следующему локатору
            # print(f"[dbg] Ошибка для селектора {selector}: {e}")
            continue

    print("[*] Кнопка 'Подтвердить другим способом' не найдена")
    return False

def get_vk_curl(driver, timeout: int = 300) -> str:
    """
    Ждём в driver.requests появления запроса к login.vk.ru/?act=web_token
    и возвращаем cURL команду этого запроса.
    """
    driver.get("https://vk.ru/id0")

    end = time.time() + timeout
    while time.time() < end:
        for req in driver.requests:
            if 'https://login.vk.ru/?act=web_token' in req.url:
                # Формируем cURL команду
                headers = ' '.join(f'-H "{k}: {v}"' for k, v in req.headers.items())
                curl_command = f"curl '{req.url}' {headers}"

                # Добавляем параметры POST-запроса, если они есть
                if req.method == 'POST':
                    try:
                        if isinstance(req.body, dict):
                            # Если body - словарь
                            data = ' '.join(f'-d "{k}={v}"' for k, v in req.body.items())
                            curl_command += f" {data}"
                        elif isinstance(req.body, bytes):
                            # Если body - байты
                            try:
                                body_str = req.body.decode('utf-8')
                                curl_command += f" -d '{body_str}'"
                            except UnicodeDecodeError:
                                # Если не удаётся декодировать как utf-8
                                hex_data = req.body.hex()
                                curl_command += f" -d '{hex_data}' --data-binary"
                        elif isinstance(req.body, str):
                            # Если body - строка
                            curl_command += f" -d '{req.body}'"
                    except Exception as e:
                        print(f"Ошибка при обработке тела запроса: {e}")

                return curl_command

        time.sleep(0.5)
    return None


def solve_simple_captcha(driver, log_signal=None, timeout=1):
    """
    Нажимает на чекбокс капчи "Я не робот" (ищет в iframe).
    """
    time.sleep(3)
    try:
        wait = WebDriverWait(driver, timeout)

        # Проверяем iframe
        print("[*] Ищем iframe с капчей...")
        if log_signal:
            log_signal.emit("[*] Ищем iframe с капчей...")

        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"[*] Найдено {len(iframes)} iframe")
        if log_signal:
            log_signal.emit(f"[*] Найдено {len(iframes)} iframe")

        captcha_element = None
        in_iframe = False

        # Сначала пробуем найти в основном контенте
        captcha_locators = [
            (By.ID, "not-robot-captcha-checkbox"),
            (By.CSS_SELECTOR, "label.vkc__Checkbox-module__Checkbox"),
            (By.XPATH, "//label[contains(., 'Я не робот')]"),
            (By.CLASS_NAME, "vkc__Checkbox-module__Checkbox"),
            (By.CSS_SELECTOR, ".vkc__CheckboxPopupCaptcha-module__checkboxBlock label"),
        ]

        # Пробуем найти в основном контенте
        for by, selector in captcha_locators:
            try:
                captcha_element = wait.until(EC.element_to_be_clickable((by, selector)))
                print(f"[+] Найден чекбокс в основном контенте: {selector}")
                if log_signal:
                    log_signal.emit(f"[+] Найден чекбокс в основном контенте: {selector}")
                break
            except TimeoutException:
                continue

        # Если не нашли, ищем в iframe
        if not captcha_element and len(iframes) > 0:
            for i, iframe in enumerate(iframes):
                try:
                    print(f"[*] Переключаемся в iframe {i}...")
                    if log_signal:
                        log_signal.emit(f"[*] Переключаемся в iframe {i}...")

                    driver.switch_to.frame(iframe)

                    # Ищем чекбокс в iframe
                    for by, selector in captcha_locators:
                        try:
                            captcha_element = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((by, selector))
                            )
                            print(f"[+] Найден чекбокс в iframe {i}: {selector}")
                            if log_signal:
                                log_signal.emit(f"[+] Найден чекбокс в iframe {i}: {selector}")
                            in_iframe = True
                            break
                        except TimeoutException:
                            continue

                    if captcha_element:
                        break
                    else:
                        driver.switch_to.default_content()

                except Exception as e:
                    print(f"[!] Ошибка при работе с iframe {i}: {e}")
                    driver.switch_to.default_content()
                    continue

        if not captcha_element:
            print("[!] Чекбокс капчи не найден")
            if log_signal:
                log_signal.emit("[!] Чекбокс капчи не найден")
            driver.switch_to.default_content()
            return False

        # Кликаем по чекбоксу
        try:
            captcha_element.click()
            print("[+] Чекбокс капчи нажат (обычный клик)")
            if log_signal:
                log_signal.emit("[+] Чекбокс капчи нажат (обычный клик)")
        except Exception as e1:
            try:
                driver.execute_script("arguments[0].click();", captcha_element)
                print("[+] Чекбокс капчи нажат (JS клик)")
                if log_signal:
                    log_signal.emit("[+] Чекбокс капчи нажат (JS клик)")
            except Exception as e2:
                try:
                    checkbox_input = captcha_element.find_element(By.TAG_NAME, "input")
                    driver.execute_script("arguments[0].click();", checkbox_input)
                    print("[+] Чекбокс капчи нажат (клик по input)")
                    if log_signal:
                        log_signal.emit("[+] Чекбокс капчи нажат (клик по input)")
                except Exception as e3:
                    print(f"[!] Все попытки клика не сработали: {e1}, {e2}, {e3}")
                    if log_signal:
                        log_signal.emit(f"[!] Все попытки клика не сработали")
                    driver.switch_to.default_content()
                    return False
    except Exception as e:
        print(f"[!] Ошибка при попытке решить капчу: {e}")
        if log_signal:
            log_signal.emit(f"[!] Ошибка при попытке решить капчу: {e}")
        try:
            driver.switch_to.default_content()
        except:
            pass
        return False
    finally:
        driver.switch_to.default_content()
        return True


def skip_phone_validation_if_exists(driver, log_signal = None, timeout=3):
    """
    Проверяет, есть ли на странице попап 'Добавление номера телефона',
    и нажимает кнопку 'Пропустить ввод номера', если он найден.

    Args:
        driver: WebDriver instance
        timeout (int): время ожидания в секундах

    Returns:
        bool: True если попап найден и пропущен, False если его не было
    """
    try:
        wait = WebDriverWait(driver, timeout)

        # Ищем ссылку "Пропустить ввод номера"
        skip_link = wait.until(EC.element_to_be_clickable(
            (By.ID, "validation_skip")
        ))

        # Кликаем по ссылке
        driver.execute_script("arguments[0].click();", skip_link)
        print("[*] Нажали 'Пропустить ввод номера'")
        if log_signal:
            log_signal.emit("[*] Нажали 'Пропустить ввод номера'")
        time.sleep(2)  # Ждём закрытия попапа
        solve_simple_captcha(driver, log_signal)
        return True
    except TimeoutException:
        # Попапа не было → просто продолжаем
        print("[!] Поп апа не было")
        return False
    except Exception as e:
        print(f"[!] Ошибка при попытке пропустить ввод номера: {e}")
        return False

def subscribe_to_public(driver, public_url: str, log_signal = None, timeout: int = 10):
    """
    Переходит по ссылке на паблик и подписывается на него.
    Сначала проверяет, подписан ли уже аккаунт.

    Args:
        driver: WebDriver instance
        public_url (str): Ссылка на паблик VK
        timeout (int): Время ожидания элементов в секундах

    Returns:
        str: Статус операции ("already_subscribed", "subscribed", "error")
    """
    try:
        public_url = vk_com_to_ru(public_url)
        print(f"[*] Переходим к паблику: {public_url}")
        if log_signal:
            log_signal.emit(f"[*] Переходим к паблику: {public_url}")
        driver.get(public_url)
        time.sleep(3)  # Ждём загрузки страницы

        wait = WebDriverWait(driver, timeout)

        # Сначала проверяем, подписаны ли уже
        try:
            # Ищем элемент "Вы подписаны"
            subscribed_element = driver.find_element(
                By.CLASS_NAME, "redesigned-group-subscribed"
            )
            if subscribed_element and "Вы подписаны" in subscribed_element.text:
                print(f"[+] Уже подписаны на {public_url}")
                if log_signal:
                    log_signal.emit(f"[+] Уже подписаны на {public_url}")
                return "already_subscribed"
        except NoSuchElementException:
            # Элемент "Вы подписаны" не найден, значит не подписаны
            pass

        # Ищем кнопку "Подписаться"
        subscribe_locators = [
            # По ID
            #(By.ID, "join_button"),
            # По классу и тексту
            (By.XPATH,
             "//button[contains(@class,'FlatButton--primary') and .//span["
             "  contains(normalize-space(.), 'Подписаться')"
             "  or contains(normalize-space(.), 'Follow')"
             "  or contains(normalize-space(.), 'Join')"
             "]]"),
            # По полному XPath (как запасной вариант)
            (By.XPATH,
             "/html/body/div[4]/div/div/div[2]/div[2]/div[3]/div/div/div[1]/div[2]/div[3]/div/aside/div/button"),
            # Более гибкий поиск по тексту
            (By.XPATH, "//button[.//span[text()='Подписаться']]"),
        ]

        subscribe_button = None
        for by, selector in subscribe_locators:
            try:
                subscribe_button = wait.until(
                    EC.element_to_be_clickable((by, selector))
                )
                print(f"[*] Найдена кнопка 'Подписаться' через селектор: {selector}")
                if log_signal:
                    log_signal.emit(f"[*] Найдена кнопка 'Подписаться' через селектор: {selector}")
                break
            except TimeoutException:
                continue

        if not subscribe_button:
            if log_signal:
                log_signal.emit(f"[!] Кнопка 'Подписаться' не найдена на {public_url}")
            print(f"[!] Кнопка 'Подписаться' не найдена на {public_url}")
            return "error"

        # Кликаем на кнопку подписки
        try:
            subscribe_button.click()
            print(f"[*] Нажали кнопку 'Подписаться'")
            if log_signal:
                log_signal.emit(f"[*] Нажали кнопку 'Подписаться'")
        except Exception as e:
            # Если обычный клик не сработал, пробуем через JavaScript
            print(f"[*] Обычный клик не сработал, пробуем через JS: {e}")
            if log_signal:
                log_signal.emit(f"[*] Обычный клик не сработал, пробуем через JS: {e}")
            driver.execute_script("arguments[0].click();", subscribe_button)

        if not skip_phone_validation_if_exists(driver, log_signal):
            print(f"[!] Не удалось скипнуть валидацию по номеру телефона")
            if log_signal:
                log_signal.emit(f"[!] Не удалось скипнуть валидацию по номеру телефона")

        time.sleep(2)  # Ждём обработки подписки

        # Проверяем, что подписка прошла успешно
        try:
            # Ждём появления элемента "Вы подписаны"
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "redesigned-group-subscribed"))
            )
            print(f"[+] Успешно подписались на {public_url}")
            if log_signal:
                log_signal.emit(f"[+] Успешно подписались на {public_url}")
            return "subscribed"
        except TimeoutException:
            print(f"[!] Не удалось подтвердить подписку на {public_url}")
            if log_signal:
                log_signal.emit(f"[!] Не удалось подтвердить подписку на {public_url}")
            return "error"

    except Exception as e:
        print(f"[!] Ошибка при подписке на {public_url}: {e}")
        if log_signal:
            log_signal.emit(f"[!] Ошибка при подписке на {public_url}: {e}")
        return "error"

def find_save_curl(driver, login: str, password: str, log_signal = None):
    print("[*] Ищем curl (Bash) на странице...")
    if log_signal:
        log_signal.emit("[*] Ищем curl (Bash) на странице...")
    curl_command = get_vk_curl_v2(driver)
    if curl_command is None:
        if log_signal:
            log_signal.emit("[-] cURL не найден")
        print("[-] cURL не найден")
        return None

    print("[*] cURL найден!")
    return curl_command

def _read_left_pct(thumb):
    style = thumb.get_attribute("style") or ""
    m = re.search(r'left:\s*([\d.]+)%', style)
    return float(m.group(1)) if m else None

def _read_step_from_left(left_pct, max_value):
    return (left_pct / 100.0) * max_value

def _read_range_value(input_el):
    try:
        v = input_el.get_attribute("value")
        return float(v) if v is not None else None
    except Exception:
        return None

def move_vk_slider_incremental(driver, best_step, timeout=10, center_bias=0.5, max_pixels_guard=400):
    """
    Инкрементально двигает слайдер по 1 px, после каждого шага читает фактическую позицию.
    Останавливается, когда достигает целевого шага.

    best_step: целевой шаг от 0 до max (обычно 49)
    center_bias: сдвиг к центру шага (0.5 = центр)
    """
    try:
        wait = WebDriverWait(driver, timeout)

        # Берём последний видимый iframe с капчей
        iframe = None
        for f in reversed(driver.find_elements(By.TAG_NAME, "iframe")):
            if f.is_displayed() and f.size.get('width',0) > 100 and f.size.get('height',0) > 100:
                driver.switch_to.frame(f)
                if driver.find_elements(By.CSS_SELECTOR, ".vkc__SwipeButton-module__track"):
                    iframe = f
                    break
                driver.switch_to.default_content()
        if not iframe:
            print("[!] Iframe капчи не найден")
            return False

        thumb = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span[data-type='thumb']")))
        track = driver.find_element(By.CSS_SELECTOR, ".vkc__SwipeButton-module__track")
        rng   = driver.find_element(By.CSS_SELECTOR, "input[type='range'][data-type='thumb']")

        max_value = float(rng.get_attribute("max"))  # 49.0
        track_w   = track.size["width"]
        thumb_w   = thumb.size["width"]
        move_area = track_w - thumb_w

        # Начальные измерения
        left_pct = _read_left_pct(thumb)
        if left_pct is None:
            left_pct = 0.0
        current_step = _read_step_from_left(left_pct, max_value)

        target_step = float(best_step) + float(center_bias)
        target_step = max(0.0, min(max_value, target_step))

        # Направление движения: вправо/влево
        direction = 1 if target_step >= current_step else -1

        print(f"[*] max={max_value:.0f}, track={track_w}, thumb={thumb_w}, move_area={move_area}")
        print(f"[*] current_step={current_step:.2f}, target_step={target_step:.2f}, direction={'right' if direction>0 else 'left'}")

        actions = ActionChains(driver)
        actions.move_to_element(thumb).pause(0.1).click_and_hold(thumb).pause(0.12).perform()

        moved_px = 0
        last_report_time = time.time()

        while True:
            # Проверка достижения цели (с допуском в 0.2 шага)
            if direction > 0 and current_step >= target_step - 0.1:
                break
            if direction < 0 and current_step <= target_step + 0.1:
                break

            # Защита от выхода за границы
            if abs(moved_px) >= max_pixels_guard or abs(moved_px) >= move_area + 4:
                print("[!] Достигнут пиксельный лимит — выходим")
                break

            # Двигаем на 1 px
            ActionChains(driver).move_by_offset(direction, 0).pause(0.01).perform()
            moved_px += direction

            # Читаем фактическую позицию каждые 1–2px для скорости
            if abs(moved_px) % 1 == 0:
                left_pct = _read_left_pct(thumb)
                if left_pct is not None:
                    current_step = _read_step_from_left(left_pct, max_value)
                else:
                    # fallback — попробовать прочесть value у input
                    val = _read_range_value(rng)
                    if val is not None:
                        current_step = val

                # лог не чаще раза в 120 мс
                if time.time() - last_report_time > 0.12:
                    print(f"    moved={moved_px}px, left={left_pct:.2f}%, step≈{current_step:.2f}")
                    last_report_time = time.time()

        # Финальная тонкая доводка на ±1–2 px к центру шага
        # вычислим промах в шагах и переведём в пиксели по локальной производной: 1 шаг ≈ move_area/max_value px
        px_per_step_est = move_area / max_value
        miss_steps = target_step - current_step
        fine_dx = int(round(miss_steps * px_per_step_est))
        if fine_dx != 0 and abs(fine_dx) <= 2:
            ActionChains(driver).move_by_offset(fine_dx, 0).pause(0.04).perform()
            moved_px += fine_dx
            left_pct = _read_left_pct(thumb) or left_pct
            current_step = _read_step_from_left(left_pct, max_value)

        # Небольшой micro-nudge вокруг точки (если не у самого правого края)
        if current_step < max_value - 0.5:
            ActionChains(driver).move_by_offset(-1, 0).pause(0.03).move_by_offset(+1, 0).pause(0.03).perform()

        # Отпускаем
        ActionChains(driver).release().perform()

        print(f"[+] Готово: moved_total={moved_px}px, final_left={left_pct:.2f}%, final_step≈{current_step:.2f}")

        driver.switch_to.default_content()
        time.sleep(0.6)
        return True

    except Exception as e:
        print(f"[!] Ошибка: {e}")
        try: driver.switch_to.default_content()
        except: pass
        return False


def solve_vk_slider_captcha(driver, log_signal = None):
    """
    Находит капчу со слайдером на странице VK, отправляет на 2Captcha и эмулирует движение слайдера.
    Работает с бинарным и сжатым телом ответа, включая zstd.
    """
    print("[*] Ищем капчу на странице...")

    if log_signal:
        log_signal.emit("[*] Ищем капчу на странице...")

    for request in driver.requests:
        if "captchaNotRobot.getContent" in request.url and request.response:
            body_bytes = request.response.body

            # Сохраняем локально для проверки
            with open("captcha_response.bin", "wb") as f:
                f.write(body_bytes)

            # Обрабатываем сжатие
            content_encoding = request.response.headers.get("Content-Encoding", "").lower()
            print(f"[*] Content-Encoding: {content_encoding}")

            try:
                if "gzip" in content_encoding:
                    body_bytes = gzip.decompress(body_bytes)
                    print("[*] Декодировано gzip сжатие")
                elif "deflate" in content_encoding:
                    body_bytes = zlib.decompress(body_bytes)
                    print("[*] Декодировано deflate сжатие")
                elif "zstd" in content_encoding or "zstandard" in content_encoding:
                    # Обработка zstd сжатия
                    dctx = zstd.ZstdDecompressor()
                    body_bytes = dctx.decompress(body_bytes)
                    print("[*] Декодировано zstd сжатие")
                else:
                    print("[*] Ответ не сжат или неизвестный формат сжатия")

            except Exception as e:
                print(f"[!] Не удалось декодировать сжатый ответ ({content_encoding}): {e}")
                # Продолжаем с исходными данными

            # Пробуем загрузить JSON
            try:
                # Пробуем разные кодировки
                encodings = ['utf-8', 'latin-1', 'windows-1251', 'cp1251']

                for encoding in encodings:
                    try:
                        body_text = body_bytes.decode(encoding)
                        data = json.loads(body_text)
                        print(f"[*] JSON успешно распарсен с кодировкой {encoding}")
                        break
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                else:
                    # Если все кодировки не сработали, пробуем с игнорированием ошибок
                    body_text = body_bytes.decode('utf-8', errors='ignore')
                    data = json.loads(body_text)
                    print("[*] JSON распарсен с игнорированием ошибок кодировки")

            except Exception as e:
                print(f"[!] Не удалось распарсить JSON: {e}")
                print(f"[!] Тело ответа (первые 200 байт): {body_bytes[:200]}")

                # Сохраним тело для отладки
                with open("debug_response.txt", "wb") as f:
                    f.write(body_bytes)
                print("[*] Полный ответ сохранен в debug_response.txt для анализа")
                return False

            if "response" not in data:
                print("[!] В ответе нет ключа 'response'")
                print(f"[!] Полный ответ: {data}")
                return False

            captcha_info = data["response"]

            # Проверяем наличие необходимых полей
            if "image" not in captcha_info or "steps" not in captcha_info:
                print("[!] В ответе капчи нет необходимых полей 'image' или 'steps'")
                print(f"[!] Captcha info: {captcha_info}")
                return False

            image_base64 = captcha_info["image"]
            steps = captcha_info["steps"]

            if log_signal:
                log_signal.emit(f"[*] Капча найдена. Шагов: {len(steps)}. Отправляем на 2Captcha...")
            print(f"[*] Капча найдена. Шагов: {len(steps)}. Отправляем на 2Captcha...")
            print(steps)

            payload = {
                "clientKey": settings.API_KEY_2CAPTCHA,
                "task": {
                    "type": "VKCaptchaImageTask",
                    "image": image_base64,
                    "steps": steps
                }
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            try:
                response = requests.post("https://api.rucaptcha.com/createTask", json=payload, headers=headers, timeout=30)

                print(f"[*] Статус ответа: {response.status_code}")
                response_data = response.json()
                print(f"[*] Ответ сервера: {response_data}")

                # ПРАВИЛЬНАЯ ПРОВЕРКА ОТВЕТА
                if response_data.get("errorId") != 0:
                    print(f"[!] Ошибка RuCaptcha: {response_data.get('errorDescription')}")
                    return False

                # errorId = 0 означает успех, проверяем наличие taskId
                if "taskId" not in response_data:
                    print(f"[!] Не удалось получить taskId: {response_data}")
                    return False

                captcha_id = response_data["taskId"]
                print(f"[*] Капча принята, ID: {captcha_id}")

            except Exception as e:
                print(f"[!] Ошибка отправки на RuCaptcha: {e}")
                return False

            # Ждём решения

            if log_signal:
                log_signal.emit("[*] Ожидаем решение...")
            print("[*] Ожидаем решение...")
            solution = None
            max_attempts = 30  # Максимум 30 попыток (2.5 минуты)
            payload = {
                "clientKey": settings.API_KEY_2CAPTCHA,
                "taskId": captcha_id,
            }
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            for attempt in range(30):  # 30 попыток по 5 секунд = 2.5 минуты
                time.sleep(5)

                try:
                    res_payload = {
                        "clientKey": settings.API_KEY_2CAPTCHA,
                        "taskId": captcha_id
                    }

                    res_response = requests.post(
                        "https://api.rucaptcha.com/getTaskResult",
                        json=res_payload,
                        headers=headers,
                        timeout=30
                    )

                    res_data = res_response.json()
                    print(
                        f"[*] Статус решения ({attempt + 1}/30): errorId={res_data.get('errorId')}, status={res_data.get('status')}")

                    # ИСПРАВЛЕННАЯ ПРОВЕРКА РЕШЕНИЯ
                    if res_data.get("errorId") == 0 and res_data.get("status") == "ready":
                        if "solution" in res_data and "best_step" in res_data["solution"]:
                            # Получаем best_step как решение
                            solution = res_data["solution"]["best_step"]
                            print(f"[*] Решение получено (best_step): {solution}")
                            break
                        else:
                            print(f"[!] Нет best_step в ответе: {res_data}")
                            break
                    elif res_data.get("errorId") != 0:
                        print(f"[!] Ошибка получения решения: {res_data.get('errorDescription')}")
                        break
                    elif res_data.get("status") == "processing":
                        continue  # Продолжаем ждать
                    else:
                        print(f"[*] Статус: {res_data.get('status')}, продолжаем ожидание...")
                        continue

                except Exception as e:
                    print(f"[!] Ошибка запроса решения: {e}")
                    continue

            if not solution:
                print("[!] Не удалось получить решение")
                return False

            print(f"[*] Решение капчи получено: {solution}")

            if log_signal:
                log_signal.emit(f"[*] Решение капчи получено: {solution}")
            # Находим слайдер
            if not move_vk_slider_incremental(driver, solution):
                print("[!] Капча не решена")
                if log_signal:
                    log_signal.emit("[!] Капча не решена")
                return False

            if log_signal:
                log_signal.emit(f"[*] Капча решена!")
            print(f"[*] Капча решена!")
            del driver.requests
            time.sleep(1)
            return True

    if log_signal:
        log_signal.emit("[!] Капча не найдена.")
    print("[!] Капча не найдена.")
    return False

def fill_login_and_continue(driver, login_value, timeout=3):
    wait = WebDriverWait(driver, timeout)

    # Селекторы для поля логина (приоритет: name → type+name → CSS по placeholder → fallback XPath)
    login_locators = [
        (By.NAME, "login"),
        (By.CSS_SELECTOR, "input[name='login'][type='tel']"),
        (By.CSS_SELECTOR, "input[placeholder^='+7'][name='login']"),
        (By.XPATH, "//input[@name='login' and @type='tel']"),
        (By.XPATH, "/html/body/div/div/div/div/div/div/div/div/div/div/div/form/div[1]/section/div[1]/div/div/div[3]/span/div/div[2]/input"),
    ]

    login_input = None
    for by, sel in login_locators:
        try:
            login_input = wait.until(EC.presence_of_element_located((by, sel)))
            # Убедимся, что видим и кликабельно
            wait.until(EC.element_to_be_clickable((by, sel)))
            break
        except Exception:
            continue

    if not login_input:
        print("[!] Поле логина не найдено")
        return False

    # Приводим в видимую область и фокус
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", login_input)
    try:
        login_input.clear()
    except Exception:
        # На некоторых масках clear не работает — удаляем через Ctrl+A + Backspace
        login_input.click()
        login_input.send_keys(u"\ue009" + "a")  # CTRL + A
        login_input.send_keys(u"\ue003")        # BACKSPACE

    # Вводим логин
    login_input.click()
    login_input.send_keys(login_value)

    # Ищем кнопку Continue: по тексту, по type=submit, по классу, и fallback XPath
    continue_locators = [
        (By.XPATH, "//button[@type='submit' and .//span[normalize-space()='Continue']]"),
        (By.XPATH, "//button[.//span[normalize-space()='Continue']]"),
        (By.CSS_SELECTOR, "button[type='submit'].vkuiButton__host"),
        (By.XPATH, "/html/body/div/div/div/div/div/div/div/div/div/div/div/form/div[2]/div[1]/button"),
    ]

    continue_btn = None
    for by, sel in continue_locators:
        try:
            continue_btn = wait.until(EC.element_to_be_clickable((by, sel)))
            break
        except Exception:
            continue

    if not continue_btn:
        print("[!] Кнопка Continue не найдена/неактивна")
        return False

    # Скролл и клик
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", continue_btn)
    try:
        continue_btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", continue_btn)

    print("[+] Логин введён и нажата кнопка Continue")
    return True

def vk_login(login: str, password: str, vkpublic = None, proxy = None, log_signal = None):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--headless=new")

    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    #options.add_argument('--disable-blink-features=AutomationControlled')
    #options.add_argument('--disable-infobars')
    #options.add_argument(f'--user-agent={get_random_user_agent()}')

    tmpdir = tempfile.mkdtemp(prefix="chrome-profile-")
    options.add_argument(f"--user-data-dir={tmpdir}")
    # обязательно изолируйте и кэш:
    options.add_argument(f"--disk-cache-dir={tmpdir}/cache")

    seleniumwire_options = {
        'proxy': {
            'http': proxy,
            'https': proxy,
        }
    }

    driver = webdriver.Chrome(options=options, seleniumwire_options=seleniumwire_options)
    #driver = webdriver.Chrome(options=options)

    driver.get("https://vk.ru/")

    wait = WebDriverWait(driver, 20)  # ждём до 10 секунд
    # Ждём появления кнопки "Войти другим способом"
    button = wait.until(EC.element_to_be_clickable(
        (By.XPATH,
         "/html/body/div[15]/div/div/div/div[3]/div/div/div[2]/div[1]/div/div/section/div/div/div/div/div/div[2]/div/button[1]")
    ))

    # Нажимаем кнопку
    button.click()

    #driver.find_element(By.ID, "index_email").send_keys(VK_LOGIN)
    #driver.find_element(By.ID, "index_pass").send_keys(VK_PASSWORD + Keys.RETURN)

    # --- Поле ввода Login ---
    login_input = wait.until(EC.presence_of_element_located(
        (By.XPATH,
         "/html/body/div[15]/div/div/div/div[3]/div/div/div[2]/div[1]/div/div/section/div/div/div/div/div/form/div[1]/div[3]/span/div/div[2]/input")
    ))
    login_input.clear()
    time.sleep(1)

    login_input.send_keys(login)

    time.sleep(3)

    # --- Кнопка Sign in ---
    sign_in_button = wait.until(EC.element_to_be_clickable(
        (By.XPATH,
         "/html/body/div[15]/div/div/div/div[3]/div/div/div[2]/div[1]/div/div/section/div/div/div/div/div/form/button[1]")
    ))
    sign_in_button.click()

    time.sleep(5)

    fill_login_and_continue(driver, login)

    time.sleep(5)

    if has_too_many_attempts_alert(driver):
        driver.quit()
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None, False

    solve_vk_slider_captcha(driver, log_signal)
    solve_simple_captcha(driver, log_signal)

    time.sleep(3)

    check_for_max_window(driver,log_signal)
    check_for_sms_window(driver,log_signal)

    #close_popup_if_exists(driver)

    time.sleep(3)

    #click_confirm_another_way_if_present(driver)


    #click_password_method(driver)

    # --- Поле ввода пароля ---
    password_input = wait.until(EC.presence_of_element_located(
        (By.XPATH, "/html/body/div/div/div/div/div/div[1]/div/div/div/div/div/form/div[1]/div[3]/div/div/input")
    ))

    # Очистка поля (на случай, если уже есть текст)
    password_input.clear()
    # Альтернатива: password_input.send_keys(Keys.CONTROL + "a", Keys.DELETE)

    # Ввод пароля
    password_input.send_keys(password)

    time.sleep(3)
    # --- Кнопка Continue ---
    continue_button = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "/html/body/div/div/div/div/div/div[1]/div/div/div/div/div/form/div[2]/button")
    ))
    continue_button.click()

    time.sleep(10)

    if has_too_many_attempts_alert(driver):
        driver.quit()
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None, False

    solve_vk_slider_captcha(driver, log_signal)
    solve_simple_captcha(driver, log_signal)

    time.sleep(3)
    curl = find_save_curl(driver, login, password, log_signal)

    time.sleep(3)

    sub = subscribe_to_public(driver, vkpublic, log_signal)

    time.sleep(3)

    print("[*] Авторизация завершена.")
    driver.quit()
    shutil.rmtree(tmpdir, ignore_errors=True)
    return curl, sub

#if __name__ == "__main__":
#    accounts = read_all_credentials()
#    for i, (login, password) in enumerate(accounts):
#        print(f"Аккаунт {i + 1}: {login}")
#        vk_login(login, password)