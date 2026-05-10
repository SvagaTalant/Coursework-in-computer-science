import streamlit as st
import plotly.express as px
from data_handler import get_enhanced_stats, export_report_to_excel
from ai_analyzer import get_ai_insight

st.set_page_config(page_title="Finance Asistant", layout="wide")

if 'data' not in st.session_state:
    st.cache_data.clear()

st.title("Система оптимізації персональних витрат ")
st.markdown("---")

uploaded_file = st.file_uploader("Завантажте виписку банківських операцій (CSV або Excel)", type=['csv', 'xlsx', 'xls'])

if uploaded_file:
    try:
        # Отримання аналітики
        data = get_enhanced_stats(uploaded_file)
        
        # Ряд метрик (Лічильники)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Загальні витрати", f"{data['total_spent']:.2f} ₴")
        col2.metric("Прогноз на місяць", f"{data['forecast']:.2f} ₴")
        col3.metric("Виявлено підписок", len(data['subscriptions']))
        col4.metric("Знайдено аномалій", len(data['anomalies']))

        st.write("---")
        
        # Графіки
        c1, c2 = st.columns(2)
        with c1:
            fig_pie = px.pie(data['cat_stats'], values='total', names='Category', 
                             title="Розподіл бюджету за категоріями", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c2:
            fig_bar = px.bar(data['cat_stats'], x='Category', y='total', 
                             title="Витрати за категоріями (₴)", color='total')
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Блок ШІ-аналітика
        st.write("---")
        with st.expander("Інтелектуальний фінансовий помічник", expanded=True):
            st.info("Поставте питання ШІ щодо ваших фінансів або попросіть поради з економії.")
            query = st.text_area("Ваш запит:", placeholder="Наприклад: Чому мої витрати зросли цього місяця?")
            
            if st.button("Отримати консультацію"):
                if query:
                    with st.spinner("Аналізую дані..."):
                        response = get_ai_insight(data, query)
                        st.markdown("### Порада від консультанта:")
                        st.success(response)
                else:
                    st.warning("Будь ласка, введіть запитання.")

        # Таблиця аномалій
        st.subheader("Нетипові витрати (Аномалії)")
        if not data['anomalies'].empty:
            st.dataframe(data['anomalies'], use_container_width=True)
        else:
            st.success("Система не виявила підозрілих витрат.")

        st.write("---")
        st.subheader("Регулярні платежі (Підписки)")
        if not data['subscriptions'].empty:
            st.dataframe(data['subscriptions'], use_container_width=True)
        else:
            st.info("Система не виявила регулярних платежів (підписок).")
            
        # Експорт
        st.write("---")
        excel_data = export_report_to_excel(data)
        st.download_button(
            label="Завантажити повний звіт (.xlsx)",
            data=excel_data,
            file_name="Finance_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Помилка обробки файлу: {str(e)}")