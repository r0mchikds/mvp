import streamlit as st
import requests
import json
import time
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE = "http://recs-api:8080"
st.set_page_config(page_title="Recommendation Service", layout="wide")
st.title("Recommendation Service (demo)")

# Session state init
if "token" not in st.session_state:
    st.session_state.token = None
    st.session_state.email = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "top_items" not in st.session_state:
    st.session_state.top_items = []
if "search_query" not in st.session_state:
    st.session_state.search_query = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "search_offset" not in st.session_state:
    st.session_state.search_offset = 10  # после первого запроса показываем 10 товаров

# Helper: logout
if st.session_state.token:
    if st.button("Выйти"):
        st.session_state.token = None
        st.session_state.user_id = None
        st.session_state.email = None
        st.session_state.page = "login"
        st.session_state.search_query = None  # сброс запроса
        st.session_state.search_offset = 10   # сброс оффсета
        st.session_state.top_items = []       # сброс товаров
        st.rerun()

# Registration page
if st.session_state.page == "register":
    st.subheader("Регистрация")
    reg_email = st.text_input("Email", key="reg_email")
    reg_password = st.text_input("Password", type="password", key="reg_pass")
    if st.button("Зарегистрироваться"):
        try:
            resp = requests.post(
                f"{API_BASE}/api/users/signup",
                json={"email": reg_email, "password": reg_password}
            )
            if resp.status_code == 201:
                st.success("Успешная регистрация! Теперь войдите в аккаунт.")
                st.session_state.page = "login"
                st.rerun()
            elif resp.status_code == 409:
                st.warning("Пользователь уже существует.")
            else:
                st.error(f"Ошибка регистрации: {resp.status_code}")
        except Exception as e:
            st.error(f"Ошибка: {str(e)}")
    if st.button("Назад к входу"):
        st.session_state.page = "login"
        st.rerun()
    st.stop()

# Login page
if st.session_state.token is None:
    st.subheader("Вход")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Войти"):
        try:
            resp = requests.post(
                f"{API_BASE}/auth/token",
                data={"username": email, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if resp.status_code == 200:
                st.session_state.token = resp.json()["RECS_API"]
                st.session_state.email = email
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                user = requests.get(f"{API_BASE}/api/users/by_email", params={"email": email}, headers=headers).json()
                if user:
                    st.session_state.user_id = user["id"]
                    logger.info(f"Успешный вход: {email}, user_id={user['id']}")
                    st.session_state.top_items = []
                    st.success("Успешный вход!")
                    st.rerun()
                else:
                    st.error("Пользователь не найден")
                    logger.warning(f"Пользователь не найден в системе: {email}")
            else:
                st.error("Неверные учетные данные")
        except Exception as e:
            st.error(f"Ошибка: {str(e)}")
    if st.button("Зарегистрироваться"):
        st.session_state.page = "register"
        st.rerun()
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

def show_items(items):
    query = st.session_state.get("search_query", "")
    query_lower = query.lower() if query else None

    for item in items:
        col1, col2 = st.columns([1, 5])
        with col1:
            st.image(item["image_url"], width=100)
        with col2:
            # Подсветка title
            title = item["title"]
            if query_lower:
                title = title.replace("\n", " ")
                title = re.sub(f"({re.escape(query)})", r"<mark>\1</mark>", title, flags=re.IGNORECASE)
                st.markdown(f"**{title}**", unsafe_allow_html=True)
            else:
                st.markdown(f"**{title}**")

            # Раскрытие описания
            desc_key = f"desc_expanded_{item['id']}"
            if desc_key not in st.session_state:
                st.session_state[desc_key] = False

            description = item["description"]
            if query_lower:
                description = description.replace("\n", " ")
                description = re.sub(f"({re.escape(query)})", r"<mark>\1</mark>", description, flags=re.IGNORECASE)

            if st.session_state[desc_key]:
                st.markdown(description, unsafe_allow_html=True)
                if st.button("Свернуть", key=f"collapse_{item['id']}"):
                    st.session_state[desc_key] = False
                    st.rerun()
            else:
                desc_short = description[:150] + "..."
                st.markdown(desc_short, unsafe_allow_html=True)
                if st.button("Показать полностью", key=f"expand_{item['id']}"):
                    st.session_state[desc_key] = True
                    st.rerun()

            if st.button("Лайкнуть", key=f"like_{item['id']}"):
                try:
                    like_resp = requests.post(
                        f"{API_BASE}/api/interaction/like",
                        headers=headers,
                        json={"user_id": st.session_state.user_id, "item_id": item["id"]}
                    )
                    if like_resp.status_code == 200:
                        st.success("Лайк сохранён!")
                        logger.info(f"Лайк сохранён: user_id={st.session_state.user_id}, item_id={item['id']}")
                    else:
                        st.error("Не удалось сохранить лайк")
                        logger.warning(f"Не удалось сохранить лайк: user_id={st.session_state.user_id}, item_id={item['id']}, status_code={like_resp.status_code}")
                except Exception as e:
                    st.error(f"Ошибка при лайке: {str(e)}")

        st.markdown("---")

def load_top_items(query=None):
    try:
        payload = {
            "user_id": st.session_state.user_id,
            "top_n": 50 if query else 10
        }
        if query:
            payload["query"] = query

        resp = requests.post(f"{API_BASE}/api/recommendation/", json=payload, headers=headers)
        if resp.status_code != 201:
            st.warning(f"Не удалось создать задачу: {resp.status_code}")
            return

        task_id = resp.json()["id"]
        max_wait_time = 30
        start_time = time.time()

        with st.spinner("Ожидание ответа от ML воркера..."):
            while True:
                status_resp = requests.get(f"{API_BASE}/api/recommendation/{task_id}", headers=headers)
                try:
                    status = status_resp.json()
                    logger.info(f"Статус задачи: {status}")
                except Exception as e:
                    logger.warning("Ошибка при разборе JSON", exc_info=True)
                    status = {}

                if status.get("result"):
                    ids = json.loads(status["result"])
                    items_resp = requests.post(
                        f"{API_BASE}/api/search/by_ids",
                        headers=headers,
                        json={"item_ids": ids}
                    )
                    if items_resp.status_code == 200:
                        st.session_state.top_items = items_resp.json()
                        if query:
                            st.session_state.search_offset = 10
                        logger.info(f"Загружено товаров: {len(st.session_state.top_items)}")
                    break

                if time.time() - start_time > max_wait_time:
                    logger.warning("Время ожидания результата истекло.")
                    break

                time.sleep(1)

    except Exception as e:
        logger.error("Ошибка при загрузке рекомендаций", exc_info=True)

# UI
with st.container():
    cols = st.columns([5, 1])
    query = cols[0].text_input("Введите запрос", value=st.session_state.search_query or "", label_visibility="collapsed")
    if cols[1].button("Поиск"):
        if query.strip():
            st.session_state.search_query = query
            st.session_state.top_items = []
            load_top_items(query=query)
            st.rerun()

col_reset, col_refresh = st.columns([2, 1])
with col_reset:
    if st.button("Сбросить поиск"):
        st.session_state.search_query = None
        st.session_state.top_items = []
        load_top_items()
        st.rerun()

with col_refresh:
    if st.button("Обновить рекомендации"):
        with st.spinner("Обновляем рекомендации..."):
            load_top_items()
            st.success("Рекомендации обновлены!")
            st.rerun()

# Show items
if not st.session_state.top_items:
    load_top_items(query=st.session_state.search_query)

if st.session_state.search_query:
    st.subheader("Результаты поиска")
    if not st.session_state.top_items:
        st.info("Ничего не найдено по вашему запросу.")
    else:
        offset = st.session_state.search_offset
        show_items(st.session_state.top_items[:offset])
        if offset < len(st.session_state.top_items):
            next_k = min(10, len(st.session_state.top_items) - offset)
            if st.button(f"Показать ещё {next_k} товаров"):
                st.session_state.search_offset += next_k
                st.rerun()
else:
    st.subheader("Рекомендованные товары")
    if not st.session_state.top_items:
        st.info("Рекомендации пока недоступны.")
    else:
        show_items(st.session_state.top_items[:10])
