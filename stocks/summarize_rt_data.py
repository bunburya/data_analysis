#!/usr/bin/env python3

from os import listdir
from os.path import join

import pandas as pd


def get_stock_data(fname: str, stocks_dir: str) -> pd.DataFrame:
    stock_data = pd.read_csv(join(stocks_dir, fname))
    stock_data.rename(columns={'timestamp': 'date', 'users_holding': fname.rstrip('.csv')}, inplace=True)
    stock_data['date'] = pd.to_datetime(stock_data['date'])
    stock_data.set_index('date', inplace=True)
    stock_data = stock_data.resample('D').mean()
    return stock_data

def main(stocks_dir: str, out_file: str):
    summary = pd.concat((get_stock_data(fname, stocks_dir) for fname in listdir(stocks_dir)), axis=1)
    summary.to_csv(out_file)

if __name__ == '__main__':
    from sys import argv
    main(argv[1], argv[2])
