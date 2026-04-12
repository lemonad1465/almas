from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

# Файл для сохранения данных
DATA_FILE = Path(__file__).resolve().parent / "almaz_air_data.json"

def load_events() -> list[dict]:
    """Загружает события из JSON файла."""
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []

def save_events(events: list[dict]) -> None:
    """Сохраняет события в JSON файл."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

def normalize_events(events: list[dict]) -> list[dict]:
    """Проверяет наличие ID у каждого события."""
    changed = False
    for e in events:
        if "id" not in e:
            e["id"] = str(uuid.uuid4())
            changed = True
    if changed:
        save_events(events)
    return events

def ensure_state() -> None:
    """Инициализирует состояние сессии Streamlit."""
    if "events" not in st.session_state:
        st.session_state.events = normalize_events(load_events())

def total_points(events: list[dict]) -> int:
    return sum(int(e.get("points", 0)) for e in events)

def points_in_range(events: list[dict], start: date, end: date) -> int:
    s = 0
    for e in events:
        try:
            d = date.fromisoformat(e["date"])
        except (KeyError, ValueError):
            continue
        if start <= d <= end:
            s += int(e.get("points", 0))
    return s

def main() -> None:
    st.set_page_config(page_title="Счётчик Алмаса", page_icon="💨", layout="wide")
    ensure_state()
    events: list[dict] = st.session_state.events

    if st.session_state.pop("added_ok", None):
        st.toast("Событие успешно зафиксировано! 🔥")

    # === ЗАГОЛОВОК И ГЛАВНЫЙ СЧЕТЧИК ===
    st.markdown("<h1 style='text-align: center;'>💨 Учёт «Воздуханства» Алмаса</h1>", unsafe_allow_html=True)

    total = total_points(events)
    
    # HTML/CSS блок для создания круглого счетчика с градиентом и тенями
    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem 0;">
            <div style="
                width: 250px;
                height: 250px;
                border-radius: 50%;
                background: linear-gradient(135deg, #FF4B4B 0%, #FF8F8F 100%);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 6rem;
                font-weight: 900;
                box-shadow: 0 10px 30px rgba(255, 75, 75, 0.4);
                border: 8px solid rgba(255, 255, 255, 0.1);
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
                transition: transform 0.3s ease;
            ">
                {total}
            </div>
            <div style="font-size: 1.2rem; font-weight: 600; text-transform: uppercase; letter-spacing: 2px; margin-top: 1.5rem; color: #888;">
                Общий индекс
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # === СТАТИСТИКА ЗА ПЕРИОДЫ ===
    today = date.today()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=6)
    month_start = today.replace(day=1)

    # Оборачиваем метрики в контейнеры с рамками для стильного вида
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        with st.container(border=True):
            st.metric("Сегодня", points_in_range(events, today, today))
    with c2:
        with st.container(border=True):
            st.metric("Вчера", points_in_range(events, yesterday, yesterday))
    with c3:
        with st.container(border=True):
            st.metric("За 7 дней", points_in_range(events, week_start, today))
    with c4:
        with st.container(border=True):
            st.metric("В этом месяце", points_in_range(events, month_start, today))
    with c5:
        with st.container(border=True):
            st.metric("Всего событий", len(events))

    st.divider()

    # === ОСНОВНОЙ РАБОЧИЙ БЛОК ===
    col_form, col_hist = st.columns((1, 1.8), gap="large")

    with col_form:
        st.subheader("📝 Добавить запись")
        with st.container(border=True):
            with st.form("add_event", clear_on_submit=True):
                ev_date = st.date_input("Дата инцидента", value=today, format="DD.MM.YYYY")
                
                # Текстовое поле вместо селектбокса
                desc = st.text_area("Описание ситуации", placeholder="Например: Обещал скинуть файл через 5 минут, но пропал на сутки...", height=100)
                
                points = st.number_input("Тяжесть (баллы)", min_value=-1000, max_value=1000, value=1, step=1)
                
                # Кнопка на всю ширину
                submitted = st.form_submit_button("Зафиксировать в истории", type="primary", use_container_width=True)

                if submitted:
                    if not desc.strip():
                        st.error("Пожалуйста, опишите, что произошло.")
                    else:
                        row = {
                            "id": str(uuid.uuid4()),
                            "date": ev_date.isoformat(),
                            "description": desc.strip(),
                            "points": int(points),
                            "created_at": datetime.now().isoformat(timespec="seconds"),
                        }
                        events.append(row)
                        st.session_state.events = events
                        save_events(events)
                        st.session_state.added_ok = True
                        st.rerun()

    with col_hist:
        st.subheader("📚 История обещаний")
        with st.container(border=True):
            if not events:
                st.info("Пока нет записей. Возможно, Алмас сдержал все обещания? (Маловероятно, добавьте событие слева).")
            else:
                rows = []
                for e in sorted(events, key=lambda x: (x.get("date", ""), x.get("created_at", "")), reverse=True):
                    try:
                        d = date.fromisoformat(e["date"]).strftime("%d.%m.%Y")
                    except (KeyError, ValueError):
                        d = e.get("date", "—")
                    rows.append(
                        {
                            "Дата": d,
                            "Описание": e.get("description", ""),
                            "Баллы": int(e.get("points", 0)),
                        }
                    )
                df = pd.DataFrame(rows)
                
                # Настройка отображения таблицы
                st.dataframe(
                    df,
                    column_config={
                        "Дата": st.column_config.TextColumn("📅 Дата", width="small"),
                        "Описание": st.column_config.TextColumn("💬 Описание ситуации", width="large"),
                        "Баллы": st.column_config.NumberColumn("🔥 Баллы", format="%d")
                    },
                    use_container_width=True, 
                    hide_index=True, 
                    height=350
                )

                st.write("") # Небольшой отступ
                with st.expander("🗑️ Управление записями (Удалить)"):
                    labels = [
                        f'{date.fromisoformat(e["date"]).strftime("%d.%m.%Y")} | {e.get("description", "")[:40]}... ({e.get("points", 0)})'
                        for e in sorted(events, key=lambda x: x.get("created_at", ""), reverse=True)
                    ]
                    ids = [e["id"] for e in sorted(events, key=lambda x: x.get("created_at", ""), reverse=True)]
                    if labels:
                        pick = st.selectbox("Выберите ошибочную запись", range(len(labels)), format_func=lambda i: labels[i])
                        if st.button("Удалить выбранное", type="secondary"):
                            rid = ids[pick]
                            st.session_state.events = [e for e in events if e.get("id") != rid]
                            save_events(st.session_state.events)
                            st.rerun()

if __name__ == "__main__":
    main()