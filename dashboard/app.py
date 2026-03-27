import os

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(page_title="Dashboard Consultoria TI", layout="wide")
st.title("📊 Painel Analítico - Gestão de Chamados")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "adminpassword")
DB_NAME = os.getenv("DB_NAME", "consultoria_db")

engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")


def load_data(query):
    return pd.read_sql(query, engine)


try:
    df_tickets = load_data("""
        SELECT t.id, c.company_name as cliente, u.full_name as responsavel, 
               cat.name as categoria, t.status, t.priority, t.opened_at, t.closed_at
        FROM tickets t
        JOIN clients c ON t.client_id = c.id
        JOIN users u ON t.user_id = u.id
        JOIN categories cat ON t.category_id = cat.id
    """)

    st.markdown("### Visão Geral")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Chamados", len(df_tickets))
    col2.metric("Chamados Abertos/Em Andamento", len(df_tickets[df_tickets["status"] != "Resolvido"]))
    col3.metric("Chamados Resolvidos", len(df_tickets[df_tickets["status"] == "Resolvido"]))

    st.markdown("---")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Status dos Chamados")
        fig_status = px.pie(df_tickets, names="status", hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_status, use_container_width=True)

    with col_chart2:
        st.subheader("Chamados por Categoria")
        fig_cat = px.bar(df_tickets, x="categoria", color="priority", barmode="group")
        st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown("---")

    st.subheader("Últimos Chamados Registrados")
    st.dataframe(df_tickets.sort_values(by="opened_at", ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"Erro ao conectar ou buscar dados no banco: {e}")
