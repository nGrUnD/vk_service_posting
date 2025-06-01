from seleniumwire import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs
import time
import json
import gzip


PROFILE_URL = "https://vk.com/al_profile.php?"


def get_vk_curl(driver, timeout: int = 60) -> str:
    """
    Ждём в driver.requests появления запроса к login.vk.com/?act=web_token
    и возвращаем cURL команду этого запроса.
    """
    driver.refresh()

    end = time.time() + timeout
    while time.time() < end:
        for req in driver.requests:
            if 'https://login.vk.com/?act=web_token' in req.url:
                # Формируем cURL команду
                curl_command = (
                    f"curl '{req.url}'"
                    f" {' '.join(f'-H \"{k}: {v}\"' for k, v in req.headers.items())}"
                )

                # Добавляем параметры POST-запроса, если они есть
                if req.method == 'POST':
                    try:
                        # Если body - словарь
                        if isinstance(req.body, dict):
                            curl_command += ' '.join(f'-d "{k}={v}"' for k, v in req.body.items())
                        # Если body - байты
                        elif isinstance(req.body, bytes):
                            try:
                                body_str = req.body.decode('utf-8')
                                curl_command += f" -d '{body_str}'"
                            except UnicodeDecodeError:
                                # Если не удаётся декодировать как utf-8
                                curl_command += f" -d '{req.body.hex()}' --data-binary"
                        # Если body - строка
                        elif isinstance(req.body, str):
                            curl_command += f" -d '{req.body}'"
                    except Exception as e:
                        print(f"Ошибка при обработке тела запроса: {e}")

                return curl_command
        time.sleep(0.5)

    raise RuntimeError("cURL не найден за отведённое время")


def get_vk_access_token(driver, timeout: int = 60) -> str:
    """
    Ждём в driver.requests появления запроса к login.vk.com/?act=web_token
    и возвращаем access_token из фрагмента URL.
    """
    #driver.get(PROFILE_URL)
    driver.refresh()

    end = time.time() + timeout
    while time.time() < end:
        for req in driver.requests:
            #print(f"URL REQ: {req.url}")
            if 'https://login.vk.com/?act=web_token' in req.url:
                print(f"URL REQ token найден: {req.response}")

                raw = gzip.decompress(req.response.body)
                text = raw.decode('utf-8')

                # токен в URL (#access_token=...)
                # или может быть в теле ответа
                print(f"req body: {text}")
                payload = json.loads(text)

                # Достаём токен
                access_token = payload.get('data', {}).get('access_token')
                if access_token:
                    print("Access Token:", access_token)
                    return access_token
        time.sleep(0.5)

    raise RuntimeError("Токен не найден за отведённое время")

def vk_manual_login(driver, login, password):
    wait = WebDriverWait(driver, 10)
    # Открываем страницу входа VK
    driver.get("https://login.vk.com/")
    # Нажимаем кнопку "Войти другим способом"
    enter_another_way = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="enter-another-way"]'))
    )
    enter_another_way.click()
    # Вводим Login (номер телефона)
    login_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="login"][placeholder^="+7"]'))
    )
    login_input.clear()
    login_input.send_keys(login)
    # Нажимаем кнопку "Войти"
    login_button = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test-id="submit_btn"]'))
    )
    login_button.click()

    # После нажатия кнопки "Войти" на странице VK должно появиться окно с OTP-полями.
    try:
        otp_inputs = wait.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, "input[name='otp-cell']")
        ))
        #update_status("OTP поля найдены. Ждём, пока вы введёте код в приложении.\n")
        #otp_code = wait_for_otp()  # Ждём, пока пользователь подтвердит код в нашем UI.
        #submit_otp(driver, otp_code)
    except Exception as e:
        print(f"Ошибка при авторизации VK OTP-код: {e}")
        #update_status("OTP шаг пропущен или произошла ошибка: " + str(e) + "\n")

    # После OTP переходим к вводу пароля.
    password_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="password"][aria-label="Введите пароль"]'))
    )
    password_input.clear()
    password_input.send_keys(password)
    # Нажимаем кнопку "Продолжить"
    continue_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(), "Продолжить")]]'))
    )
    continue_button.click()
    # Дополнительное ожидание до завершения авторизации
    time.sleep(3)
    print("Авторизация успешна!")
    #update_status("Авторизация успешно завершена.\n")

def get_vk_account_curl_from_browser(login, password):
    # Запуск Selenium
    options = Options()
    options.add_argument("--headless=new")         # Новый headless-режим (Chrome 112+)
    options.add_argument("--no-sandbox")  # Обход ограничений безопасности
    options.add_argument("--disable-gpu")  # Отключаем GPU-ускорение
    options.add_argument("--disable-blink-features")
    options.add_argument("--disable-blink-features=AutomationControlled")
    #options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.4430.212 Safari/537.36")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    options.set_capability("goog:loggingPrefs", {"performance": "ALL"}) # logging set all


    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.4430.212 Safari/537.36"
    })
    driver.execute_cdp_cmd("Network.enable", {})

    vk_manual_login(driver, login, password)
    vk_curl = get_vk_curl(driver)
    driver.quit()
    return vk_curl