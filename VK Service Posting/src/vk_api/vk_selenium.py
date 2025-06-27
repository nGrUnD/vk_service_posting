from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from seleniumwire import webdriver
from src.utils.rand_user_agent import get_random_user_agent
import asyncio
import time

def get_vk_curl(driver, timeout: int = 60) -> str:
    """
    Ждём в driver.requests появления запроса к login.vk.com/?act=web_token
    и возвращаем cURL команду этого запроса.
    """
    print("get vk curl")
    driver.get("https://vk.com/id0")

    end = time.time() + timeout
    while time.time() < end:
        for req in driver.requests:
            if 'https://login.vk.com/?act=web_token' in req.url:
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

    raise RuntimeError("cURL не найден за отведённое время")

def vk_manual_login(driver, login, password):
    print("login")
    wait = WebDriverWait(driver, 30)
    # Открываем страницу входа VK
    driver.get("https://login.vk.com/")

    #for request in driver.requests:
    #    # проверяем только успешные ответы
    #    if request.response:
    #        print(f"URL: {request.url}")
    #        print(f"User-Agent: {request.headers.get('User-Agent')}\n")

    js_ua = driver.execute_script("return navigator.userAgent")
    print("navigator.userAgent in browser:", js_ua)

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
        alt_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//span[contains(text(), 'Confirm using other method')]")
        ))
        alt_button.click()

        password_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[@role='button' and .//span[text()='Password']]")
        ))
        password_button.click()

    except Exception:
        print("Не получилось найти кнопку Confirm using other method")

    # После OTP переходим к вводу пароля.
    password_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="password"][aria-label="Enter password"]'))
    )
    password_input.clear()
    password_input.send_keys(password)
    # Нажимаем кнопку "Продолжить"
    continue_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//button[.//span[contains(text(), "Continue")]]'))
    )
    continue_button.click()
    # Дополнительное ожидание до завершения авторизации
    time.sleep(3)
    print("Авторизация успешна!")

def get_vk_account_curl_from_browser(login: str, password: str) -> str:
    # 1) Настраиваем фильтры для random_user_agent

    def async_wrapper():
        # Конфигурация ChromeOptions

        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--headless=new')  # ВКЛЮЧАЕМ headless режим
        options.add_argument(f'--user-agent={get_random_user_agent()}')

        seleniumwire_options = {
            'disable_encoding': True
        }

        driver = webdriver.Chrome(
            options=options,
            seleniumwire_options=seleniumwire_options
        )

        try:
            # Асинхронное выполнение синхронных операций
            #await asyncio.to_thread(driver.execute_cdp_cmd, "Network.setUserAgentOverride", {
            #    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            #})

            vk_manual_login(driver, login, password)
            curl = get_vk_curl(driver)
            driver.quit()
            return curl
        finally:
            driver.quit()

    return async_wrapper()
