import time, sys, os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit_authenticator as stauth
from streamlit_option_menu import option_menu
import sqlite3
import yaml
from yaml.loader import SafeLoader

# -------------------- DB 관리 -------------------- #
# SQLite Connect
def create_con():
    try:
        conn = sqlite3.connect(db_file)
    except Exception as e:
        st.write(e)

    return conn

# File Upload
def upload_data():
    conn = create_con()
    table_name = f'{cat_list[st.session_state.category][1:cat_list[st.session_state.category].index(" ")-1]}'
    uploaded_file = st.file_uploader('**🗂️ Choose a file**', label_visibility='collapsed')
    if uploaded_file is not None:
       # Read csv
        try:
            df = pd.read_csv(uploaded_file, encoding='cp949')
            st.write('**Data loaded successfully. These are the first 3 rows.**')
            st.dataframe(df.head(3), use_container_width=True)
        
            col1, col2 = st.columns([8,1])
            is_apply = col2.button('Update', use_container_width=True)
            if is_apply:
                pg_bar = col1.progress(0, text="⏩Progress")
                for percent_complete in range(100):
                    time.sleep(0.01)
                    pg_bar.progress(percent_complete + 1, text="Progress")
                    df.to_sql(name=table_name, con=conn, if_exists='replace', index=False)

                time.sleep(0.1)
                st.success("업데이트가 완료되었습니다.")
                time.sleep(1)
                st.session_state.page = 1
                st.rerun()

        except Exception as e:
            st.write(e)

# Data Load
def get_db(num=None):

    con = create_con()
    if num is None:
        df = pd.read_sql('SELECT * FROM Total', con)
    else:
        table_name = f'{cat_list[st.session_state.category][1:cat_list[st.session_state.category].index(" ")-1]}'
        df = pd.read_sql(f'SELECT * FROM `{table_name}`', con)

        df['Year'] = df['Year'].astype(str)
        calculate(num, df)
        df['Emission_unit'] = ['tCO2e' for _ in range(len(df))]
        
        pivot_df = df.groupby('Year')['Emission'].sum().reset_index()
        pivot_df['Category'] = cat_list[st.session_state.category][1:cat_list[st.session_state.category].index(" ")-1]
        pivot_df['Unit'] = ['tCO2e' for _ in range(len(pivot_df))]
        upsert_data(pivot_df)

    return df

# Calculate Emission
def calculate(num, df):
    if num in [0]:
        df['Emission'] = df['Weight'] * df['Conversion'] * df['Factor'] / 1000
    elif num == 1:
        df['Emission'] = df['Cost'] * df['Factor']
    elif num in [2,3,10]:
        df['Emission'] = df['Amount'] * df['Conversion'] * df['Factor']
    elif num == 4:
        df['Emission'] = df['Total_Waste'] * df['Conversion'] * (df['Ratio_Recycle']*df['Factor_Recycle']+df['Ratio_Incineration']*df['Factor_Incineration']+df['Ratio_Landfill']*df['Factor_Landfill']) / 1000
    elif num in [5,6]:
        df['Emission'] = df['Distance'] * df['Factor']
    elif num == 7:
        df['Emission'] = df['Leased_Area'] * df['Conversion'] * df['Factor']
    elif num in [8,13]:
        df['Emission'] = df['Amount'] * df['Factor']
    elif num == 9:
        df['Emission'] = df['Year_Sales'] * df['Conversion'] * df['Factor']
    elif num == 11:
        df['Emission'] = df['Total_Waste'] * df['Conversion'] * (df['Ratio_Recycle']*df['Factor_Recycle']+df['Ratio_Incineration']*df['Factor_Incineration']+df['Ratio_Landfill']*df['Factor_Landfill'])
    elif num == 12:
        df['Emission'] = df['Year_Sales'] * df['Factor']
    elif num == 14:
        df['Emission'] = df['Emission_Scope1'] + df['Emission_Scope2']
    
    if num in [1,2,3,5,6,8,12]:
        df['Emission'] = df['Emission'] / 1000

# Update Or Insert
def upsert_data(df):
    conn = create_con()
    cursor = conn.cursor()
    for i in range(len(df)):
        # 동일한 id 값이 있는지 확인
        existing_id = pd.read_sql(f"SELECT * FROM Total WHERE Year={df.loc[i,'Year']} and Category='{df.loc[i,'Category']}';", conn)
        if len(existing_id) == 0:
            # 동일한 id가 없으면 새로운 레코드 삽입
            cursor.execute(f"INSERT INTO Total VALUES ({df.loc[i,'Year']}, '{df.loc[i,'Category']}', {df.loc[i,'Emission']}, '{df.loc[i,'Unit']}');")
        else:
            # 동일한 id가 있으면 기존 레코드 업데이트
            cursor.execute(f"UPDATE Total SET Year={df.loc[i,'Year']}, Category='{df.loc[i,'Category']}', Emission={df.loc[i,'Emission']}, Unit='{df.loc[i,'Unit']}' WHERE Year={df.loc[i,'Year']} and Category='{df.loc[i,'Category']}';")

        conn.commit()
    conn.close()

def convert_df(df):
    return df.to_csv(index=False).encode('cp949')

# -------------------- 페이지 구성 -------------------- #
# SIDEBAR
def set_sidebar():
    st.sidebar.write("---")
    st.sidebar.text("본 시스템은 OOO의 Scope3 관리를 위해\n파이썬의 Streamlit 모듈로 제작되었으며,\n\n연간 Scope3 온실가스 배출량을 산정하고\n산정 결과를 시각화하는 시스템입니다.")
    st.sidebar.write("---")
    st.sidebar.write("## 🔍Select Options")
    y_selected = st.sidebar.selectbox("연도", range(2022, 2023), index=st.session_state.year-2022,
                                        key='year_select',label_visibility="collapsed", disabled=not(st.session_state.login))
    cat_selected = st.sidebar.selectbox("카테고리", cat_list, index=st.session_state.category,
                                        key='category_select', label_visibility="collapsed", disabled=not(st.session_state.login))
    if st.sidebar.button("**Emission Value**", use_container_width=True, disabled=not(st.session_state.login)):
        st.session_state.year = y_selected
        st.session_state.category = cat_list.index(cat_selected)
        st.session_state.page = 1
        st.rerun()
    if st.sidebar.button("**Data Analysis**", use_container_width=True, disabled=not(st.session_state.login)):
        st.session_state.year = y_selected
        st.session_state.category = cat_list.index(cat_selected)
        st.session_state.page = 3
        st.rerun()
    
    st.sidebar.write("---")
    st.sidebar.write("@ made_by :green[ECOEYE]🌱")

# PAGE0 : Home
def get_page0():
    st.write('<div style="font-size: 60px; font-weight: bold;"> Scope3 :: GHG Emission Tool ⚒️ </div>', unsafe_allow_html=True)
    st.write("---")
    with st.container():
        st.write(f'<div style="font-size: 40px; font-weight: bold; color:white; background-color: steelblue; padding-left: 10px; padding-bottom: 5px; margin-bottom: 5px; text-align: center;"> {st.session_state.year} Scope3 Category 1~15 </div>', unsafe_allow_html=True)
        df = get_db()
        table = pd.pivot_table(df[df['Year']==st.session_state.year], index=['Category'], values='Emission', aggfunc='sum').reset_index()
        table['num'] = table['Category'].str.replace('C', '').astype(int)
        table['Percent'] = np.round(table['Emission'] / sum(table['Emission']) * 100,2).astype(str) + "%"
        table = table.sort_values('num')
        del table['num']
        fig = go.Figure(go.Bar(x=table['Category'], y=table['Emission'], marker=dict(color='steelblue')))
        fig.update_traces(text=table['Percent'], textposition='outside', textfont=dict(size=15, color='black'))
        fig.update_layout(font=dict(size=13, color='black'), height=300, xaxis=dict(title='Category'), yaxis=dict(title='Emission', range=[0, table['Emission'].max()*1.2]), margin=dict(l=50,r=30,t=20,b=50), paper_bgcolor="#F7F7F7", plot_bgcolor="#F7F7F7")
        fig.update_xaxes(tickvals=table.index, tickmode='array')
        st.plotly_chart(fig, use_container_width=True)
    col1, col2 = st.columns([1,1])
    with col1:
        st.write('<div style="font-size: 30px; font-weight: bold; margin-bottom:15px; text-align:center; padding:5px 0px 10px 0px; border:3px outset lightgray;"> I. Upstream ⬆️ </div>', unsafe_allow_html=True)
        for i in range(0,8):
            if st.button(cat_list[i]):
                st.session_state.category = i
                st.session_state.page = 1
                st.rerun()
    with col2:
        st.write('<div style="font-size: 30px; font-weight: bold; margin-bottom:15px; text-align:center; padding:5px 0px 10px 0px; border:3px outset lightgray;"> II. Downstream ⬇️ </div>', unsafe_allow_html=True)
        for i in range(8,15):
            if st.button(cat_list[i]):
                st.session_state.category = i
                st.session_state.page = 1
                st.rerun()

    st.write("---")
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        go_0 = st.button("**Category List**", key="go_0_button", use_container_width=True, disabled=True)
        if go_0:
            st.session_state.page = 0
            st.rerun()
    with c2:
        go_1 = st.button("**Emission Value →**", key="go_1_button", use_container_width=True)
        if go_1:
            st.session_state.page = 1
            st.rerun()
    with c3:
        go_3 = st.button("**Data Analysis →**", key="go_3_button", use_container_width=True)
        if go_3:
            st.session_state.page = 3
            st.rerun()

# PAGE1 : Emission
def get_page1():
    st.write('<div style="font-size: 60px; font-weight: bold;"> Scope3 :: GHG Emission DB 🧮</div>', unsafe_allow_html=True)
    tabs = st.tabs(['**2022**'])
    with tabs[0]:
        st.write(f'<div style="font-size: 30px; font-weight: bold; color:white; background-color: steelblue; padding-left: 10px; padding-bottom: 5px; margin-bottom:15px;"> {cat_list[st.session_state.category]} </div>', unsafe_allow_html=True)
        df = get_db(st.session_state.category)
        co1, co2, co3 = st.columns([10,0.5,0.5])
        with co1:
            st.write(f'<div style="font-size: 20px; padding-left: 10px; padding-bottom: 5px; margin-bottom:15px;"> ✔️ Total Emissions : {df["Emission"].sum():,.2f} {df.loc[0,"Emission_unit"]} </div>', unsafe_allow_html=True)
        if st.session_state.category != 0:
            if co2.button('←', use_container_width=True):
                st.session_state.category = st.session_state.category - 1
                st.session_state.page = 1
                st.rerun()
        else:
            co2.button('←', use_container_width=True, disabled=True)
        if st.session_state.category != 14:
            if co3.button('→', use_container_width=True):
                st.session_state.category = st.session_state.category + 1
                st.session_state.page = 1
                st.rerun()
        else:
            co3.button('→', use_container_width=True, disabled=True)
        st.dataframe(df, use_container_width=True)

    col1, col2, col3 = st.columns([1,7,1])
    csv = convert_df(df)
    is_download = col1.download_button(label='Download', data=csv, file_name=f'{cat_list[st.session_state.category]}.csv', mime='text/csv', use_container_width=True)
    if is_download:
        st.success("CSV file Downloaded.")
    is_update = col3.button('Update', use_container_width=True)
    if is_update:
        st.session_state.page = 2
        st.rerun()
    
    st.write("---")
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        go_0 = st.button("**← Category List**", key="go_0_button", use_container_width=True)
        if go_0:
            st.session_state.page = 0
            st.rerun()
    with c2:
        go_1 = st.button("**Emission Value**", key="go_1_button", use_container_width=True, disabled=True)
        if go_1:
            st.session_state.page = 1
            st.rerun()
    with c3:
        go_3 = st.button("**Data Analysis →**", key="go_3_button", use_container_width=True)
        if go_3:
            st.session_state.page = 3
            st.rerun()

# PAGE2 : Update
def get_page2():
    st.write('<div style="font-size: 60px; font-weight: bold;"> Scope3 :: GHG Emission DB 🧮</div>', unsafe_allow_html=True)
    tabs = st.tabs(['**2022**'])
    with tabs[0]:
        st.write(f'<div style="font-size: 30px; font-weight: bold; color:white; background-color: steelblue; padding-left: 10px; padding-bottom: 5px; margin-bottom:15px;"> {cat_list[st.session_state.category]} </div>', unsafe_allow_html=True)
        df = get_db(st.session_state.category)
        co1, co2, co3 = st.columns([10,0.5,0.5])
        with co1:
            st.write(f'<div style="font-size: 20px; padding-left: 10px; padding-bottom: 5px; margin-bottom:15px;"> ✔️ Total Emissions : {df["Emission"].sum():,.2f} {df.loc[0,"Emission_unit"]} </div>', unsafe_allow_html=True)
        if st.session_state.category != 0:
            if co2.button('←', use_container_width=True):
                st.session_state.category = st.session_state.category - 1
                st.session_state.page = 1
                st.rerun()
        else:
            co2.button('←', use_container_width=True, disabled=True)
        if st.session_state.category != 14:
            if co3.button('→', use_container_width=True):
                st.session_state.category = st.session_state.category + 1
                st.session_state.page = 1
                st.rerun()
        else:
            co3.button('→', use_container_width=True, disabled=True)
        st.dataframe(df, use_container_width=True)
        st.write("---")

        st.write(f'<div style="font-size: 30px; font-weight: bold; color:white; background-color: seagreen; padding-left: 10px; padding-bottom: 5px; margin-bottom: 15px;"> {cat_list[st.session_state.category][:cat_list[st.session_state.category].index(" ")]} File Upload </div>', unsafe_allow_html=True)
        upload_data()
    st.write("---")
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        go_0 = st.button("**← Category List**", key="go_0_button", use_container_width=True)
        if go_0:
            st.session_state.page = 0
            st.rerun()
    with c2:
        go_1 = st.button("**Emission Value**", key="go_1_button", use_container_width=True)
        if go_1:
            st.session_state.page = 1
            st.rerun()
    with c3:
        go_3 = st.button("**Data Analysis →**", key="go_3_button", use_container_width=True)
        if go_3:
            st.session_state.page = 3
            st.rerun()

# Page3 : Analysis
def get_page3():
    st.write('<div style="font-size: 60px; font-weight: bold;"> Scope3 :: Data Analysis 📊</div>', unsafe_allow_html=True)
    st.write("---")
    col1, col2, col3 = st.columns([1, 0.1, 4])
    with col1:
        selected = option_menu(
            menu_title = None,
            options = ["Categories", "Trend by Year"],
            icons = ['graph-up', 'bar-chart-line-fill'],
            # orientation = 'horizontal',
    )
    with col3:
      ### Bar Chart
        if selected == "Categories":
            st.write('<div style="font-size: 30px; font-weight: bold; color: white; background-color: steelblue; padding-left: 10px; padding-bottom: 5px; margin: 2px 0px 15px;"> ⊙ Comparison of GHG Emissions by Category </div>', unsafe_allow_html=True)
            df = get_db()
            with st.container():
                col1, col2 = st.columns([2,1])
                with col1:
                    table = pd.pivot_table(df[df['Year']==st.session_state.year], index=['Category'], values='Emission', aggfunc='sum').reset_index()
                    table['num'] = table['Category'].str.replace('C', '').astype(int)
                    table['Percent'] = np.round(table['Emission'] / sum(table['Emission']) * 100,2).astype(str) + "%"
                    table = table.sort_values('num')
                    colors = ['#F87474' if i-1 == st.session_state.category else '#C7C7C7' for i in table['num']]
                    del table['num']
                    fig = go.Figure(go.Bar(x=table['Category'], y=table['Emission'], marker=dict(color=colors)))
                    fig.update_layout(font=dict(size=13), xaxis=dict(title='Category'), yaxis=dict(title='Emission', range=[0, table['Emission'].max()*1.2]), margin=dict(t=0,b=0))
                    fig.update_xaxes(tickvals=table.index, tickmode='array')
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.dataframe(table.set_index('Category'), use_container_width=True)
                st.write("---")
      ### Line Chart
        if selected == "Trend by Year":
            st.write('<div style="font-size: 30px; font-weight: bold; color: white; background-color: steelblue; padding-left: 10px; padding-bottom: 5px; margin: 2px 0px 15px;"> ⊙ Trend in GHG Emissions by Year </div>', unsafe_allow_html=True)
            with st.container():
                st.write('<div style="font-size: 30px; font-weight: bold; color: #6E6E6E;"> ㅡ All Categories </div>', unsafe_allow_html=True)
                col1, col2 = st.columns([2,1])
                with col1:
                    df = get_db()
                    table = pd.pivot_table(df, index=['Year'], values='Emission', aggfunc='sum')
                    fig = make_subplots(rows=1, cols=1)
                    text = ['{:,.2f}'.format(value) for value in table['Emission']]
                    fig.add_trace(go.Scatter(x=table.index, y=table['Emission'], mode="lines+markers+text", marker=dict(color="#3AB0FF"), text=text, textposition="top center"), row=1, col=1)
                    y_min = table['Emission'].min()
                    y_max = table['Emission'].max()
                    fig.update_layout(font=dict(size=13), xaxis=dict(title='Year'), yaxis=dict(title='Emission'), height=300, margin=dict(t=0,b=0))
                    fig.update_xaxes(tickvals=table.index, tickmode='array')
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.dataframe(table, use_container_width=True)
                st.write("---")
            with st.container():
                st.write(f'<div style="font-size: 30px; font-weight: bold; color: #6E6E6E;"> ㅡ {cat_list[st.session_state.category]} </div>', unsafe_allow_html=True)
                col1, col2 = st.columns([2,1])
                with col1:
                    df = get_db(st.session_state.category)
                    table = df.pivot_table(index='Year', values='Emission', aggfunc='sum')
                    fig = make_subplots(rows=1, cols=1)
                    text = ['{:,.2f}'.format(value) for value in table['Emission']]
                    fig.add_trace(go.Scatter(x=table.index, y=table['Emission'], mode="lines+markers+text", marker=dict(color="#3AB0FF"), text=text, textposition="top center"), row=1, col=1)
                    y_min = table['Emission'].min()
                    y_max = table['Emission'].max()
                    fig.update_layout(font=dict(size=13), xaxis=dict(title='Year'), yaxis=dict(title='Emission'), height=300, margin=dict(t=0,b=0))
                    fig.update_xaxes(tickvals=table.index, tickmode='array')
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.dataframe(table, use_container_width=True)
                st.write("---")

    st.write("---")
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        go_0 = st.button("**← Category List**", key="go_0_button", use_container_width=True)
        if go_0:
            st.session_state.page = 0
            st.rerun()
    with c2:
        go_1 = st.button("**← Emission Value**", key="go_1_button", use_container_width=True)
        if go_1:
            st.session_state.page = 1
            st.rerun()
    with c3:
        go_3 = st.button("**Data Analysis**", key="go_3_button", use_container_width=True, disabled=True)
        if go_3:
            st.session_state.page = 3
            st.rerun()

def get_login():

    authentication_status = st.session_state.login

    # hashed_passwords = stauth.Hasher(passwords).generate()
    with open(config_file) as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )

    name, authentication_status, username = authenticator.login('**Login**', 'main')

    if authentication_status:
        authenticator.logout('**Logout**', 'main')
    elif authentication_status == False:
        st.error('Username/password is incorrect')
    elif authentication_status == None:
        st.warning('Please enter your username and password')

    st.session_state.login = authentication_status

# --------------------- 메인 함수 --------------------- #

def main():

  # Page Configuration
    st.set_page_config(
        page_title="Scope3 온실가스 배출량 산정 툴",
        page_icon="🌱",
        layout="wide",
        initial_sidebar_state="auto",
        menu_items={
            'Get Help': 'mailto:donumm64@ecoeye.com',
            'About': "##### 주식회사 에코아이 \n ##### ECOEYE Corporation \n 지속가능사업본부 / 강지원"
        }
    )

  # Session State
    st.session_state = st.session_state
    if 'login' not in st.session_state:
        st.session_state.login = None
    if 'page' not in st.session_state:
        st.session_state.page = 0
    if 'year' not in st.session_state:
        st.session_state.year = 2022
    if 'category' not in st.session_state:
        st.session_state.category = 0

  # 카테고리 설정
    global cat_list
    cat_list = ["[C1] Purchased Goods", "[C2] Capital Goods", "[C3] Fuel and Energey-Related Activities", "[C4] Upstream Transportation and Distribution", "[C5] Waste Generated in Operations",
                "[C6] Business Travel", "[C7] Employee Commuting", "[C8] Upstream Leased Assets", "[C9] Downstream Transportation and Distribution", "[C10] Processing of Sold Products",
                "[C11] Use of Sold Products", "[C12] End-of-Life Treatment of Sold Products", "[C13] Downstream Leased Assets", "[C14] Franchises", "[C15] Investments"]

  # 파일 전달
    global db_file, config_file
    if len(sys.argv) > 1:
        db_file = sys.argv[1]
        config_file = sys.argv[2]
    else:
        db_file = "./db.db"
        config_file = "./config.yaml"

    if st.sidebar.button('**GO HOME🏠**', use_container_width=True):
        st.session_state.page = 0
        st.rerun()

  # 사이드바 설정
    set_sidebar()
    get_login()
    
    # 페이지 이동
    if st.session_state.login:
        if st.session_state.page == 0:
            get_page0()
        elif st.session_state.page == 1:
            get_page1()
        elif st.session_state.page == 2:
            get_page2()
        elif st.session_state.page == 3:
            get_page3()

if __name__ == "__main__":

    main()