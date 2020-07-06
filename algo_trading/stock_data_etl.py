#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import listdir
from os.path import join
from datetime import datetime, timedelta
import logging

import pandas as pd
import yfinance as yf
import sqlite3


ROBINTRACK_DIR = 'data_files/robintrack/stocks'
SP500_URL = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'

DB_TABLES = {
    'tickers': """CREATE TABLE IF NOT EXISTS \"{table_name}\" (
        ticker PRIMARY KEY,
        stock_name TEXT,
        gics_sector TEXT,
        gics_sub_industry TEXT,
        hq_location TEXT,
        date_added TEXT,
        cik TEXT,
        founded TEXT
    )""",
    'stock_data': """CREATE TABLE IF NOT EXISTS \"{table_name}\" (
        date TEXT NOT NULL,
        ticker TEXT NOT NULL,
        robinhood_holders REAL,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        dividends REAL,
        stock_splits REAL,
        PRIMARY KEY(date,ticker)
    )"""
}
   
def fix_col_labels(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
    """Fix column labels in a DataFrame by lower-casing and converting
    spaces to underscores, making the column names more appropriate for
    inclusion in a database.
    """
    if not inplace:
        df = df.copy()
    df.columns = df.columns.str.lower().str.replace(' ', '_')
    return df

def get_sp500_data() -> pd.DataFrame:
    sp500_data = pd.read_html(SP500_URL)[0]
    sp500_data.drop('SEC filings', inplace=True)
    sp500_data.rename({
        'Symbol': 'ticker',
        'Security': 'stock_name',
        'GICS Sector': 'gics_sector',
        'GICS Sub Industry': 'gics_sub_industry',
        'Headquarters Location': 'hq_location',
        'Date first added': 'date_added',
        'CIK': 'cik',
        'Founded': 'founded'
    }, inplace=True)
    sp500_data.set_index('ticker', inplace=True)
    return sp500_data
        

def get_robintrack_data(ticker: str, stocks_dir: str) -> pd.DataFrame:
    fname = f'{ticker.upper()}.csv'
    stock_data = pd.read_csv(join(stocks_dir, fname))
    stock_data.rename(columns={'timestamp': 'date', 'users_holding': 'robinhood_holders'}, inplace=True)
    stock_data['date'] = pd.to_datetime(stock_data['date']).dt.normalize()
    stock_data.set_index('date', inplace=True)
    stock_data = stock_data.resample('D').mean()
    fix_col_labels(stock_data, inplace=True)
    return stock_data

def get_stock_data(ticker: str) -> pd.DataFrame:
    rt_history = get_robintrack_data(ticker, ROBINTRACK_DIR)
    # For some reason, yfinance fetches one day before start_date
    start_date = rt_history.index[0].date() + timedelta(days=1)
    yf_history = yf.Ticker(ticker).history(start=start_date)
    stock_data = pd.concat((rt_history, yf_history), axis=1)
    stock_data['ticker'] = ticker # for indexing in SQL
    stock_data.columns = stock_data.columns.str.lower().str.replace(' ', '_')
    return stock_data

def write_stock_data_to_db(ticker: str, conn: sqlite3.Connection):
    """Fetch historical data for a stock ticker and write it to the database.
    Assumes that table 'stock_data' exists and that the relevant ticker
    is not already included.
    """
    logging.info(f'Writing historical data for ticker {ticker} to table stock_data.')
    stock_data = get_stock_data(ticker)
    stock_data.to_sql('stock_data', conn, if_exists='append')

def create_db_tables(cursor: sqlite3.Cursor, drop_first: bool = True):
    if drop_first:
        for table_name in DB_TABLES:
            logging.info(f'Dropping table {table_name}.')
            try:
                cursor.execute(f'DROP TABLE "{table_name}"')
            except sqlite3.OperationalError:
                # Table probably doesn't exist, which is fine
                pass
    for table_name in DB_TABLES:
        logging.info(f'Creating table {table_name}.')
        cursor.execute(DB_TABLES[table_name].format(table_name=table_name))

def main(db_file: str):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    create_db_tables()
    sp500_data = get_sp500_data()
    sp500_data.to_sql(conn)
    for ticker in sp500_data.index:
        write_stock_data_to_db(ticker, conn)
    
        
