import time
import json
import requests
import pandas as pd
import csv
from pathlib import Path
from tqdm import tqdm
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from crack import *
from last_step import Filter
class STOCK_RAVEN:
    def _collect_stock(self):
        print("Start Collecting Stock data for 20 trading days...")
        day_searched = 0
        today = datetime.now()
        stocks = {}
        url = "http://www.twse.com.tw/exchangeReport/MI_INDEX"
        query_params = {
            "date": "",
            "response": "json",
            "type": "ALL",
        }
        while day_searched < 20:
            date = today.strftime("%Y%m%d")
            today = today + timedelta(days=-1)
            query_params["date"] = date
            try:
                page = requests.get(url, params=query_params)
            except:
                print(f"retry {date}")
            time.sleep(5) #prevent  anti-web crawling system
            if page.json()["stat"] == "OK":
                day_searched += 1
                print(f"{date} added")
                if day_searched == 10:
                    time.sleep(10) #prevent anti-web crawling system
                for stock in page.json()["data9"]:
                    if stock[0] not in stocks:
                        try:
                            stocks[stock[0]] = {
                                "name": stock[1],
                                "price": [float(stock[8])],
                                "volume": [int(stock[2].replace(",", ""))],
                            }
                        except:
                            pass
                    else:
                        try:
                            stocks[stock[0]]["price"].append(float(stock[8]))
                            stocks[stock[0]]["volume"].append(
                                int(stock[2].replace(",", ""))
                            )
                        except:
                            del stocks[stock[0]]
        today = datetime.now().strftime("%Y%m%d")
        with open(f"{today}_20days_data.json", "w") as file:
            json.dump(stocks, file)
        return stocks

    def qualified_stock(self, twenty_day_info):
        stocks = twenty_day_info
        qualified = []
        for k, v in stocks.items():
            if len(v["price"]) == 20:
                if (
                    (sum(v["price"][:5]) / 5) < (sum(v["price"][:10]) / 10)
                    and v["price"][0] > (sum(v["price"][:20]) / 20)
                    and (sum(v["volume"][:5]) / 5) > 1000000
                    and v["price"][0] > (sum(v["price"][:5]) / 5)
                    and v["volume"][0] > v["volume"][1]
                ):
                    qualified.append((k, v["name"]))
        print(f"Number of Qualified Stocks: ({len(qualified)} )")
        file_name = datetime.now().strftime('%Y_%m_%d') + '_stock.csv'
        file_path = Path('data', file_name)
        file_path.touch()
        with open(file_path, 'w') as out:
            csv_out=csv.writer(out)
            csv_out.writerow(['Stock_code','Name'])
            for row in qualified:
                csv_out.writerow(row)
        for qualified_stock in qualified:
            print(qualified_stock)
        while True:
            print("Enter 'leave' to leave: ")
            code = input()
            if code in stocks:
                print(stocks[code]["name"])
                print(f'Closing Price : {stocks[code]["price"][0]}\n')
                print(f'avg price for 5 days : {round(sum(stocks[code]["price"][:5])/5,2)}\n')
                print(f'avg price for 10 days : {round(sum(stocks[code]["price"][:10])/10,2)}\n')
                print(f'avg price for 20 days : {round(sum(stocks[code]["price"][:20])/20,2)}\n')
                print(f'Volumes for 5 days : {sum(stocks[code]["volume"][:5])/5}\n')
                print("Closing price for 20 days :")
                for price in stocks[code]["price"]:
                    print(f"{price} 元")
                print("\n Volumes for 20 days(1000) :")
                for volume in stocks[code]["volume"]:
                    print(f"{volume} ")
            elif code.lower() == "leave":
                break
            else:
                print(f"{code} 此股不符合條件")
        return "DONE"


class INS_RAVEN:
    def _get_major_institutions(self):
        near_five_days_info = {}
        day = 0
        while len(near_five_days_info) < 5:
            today = (datetime.now() + timedelta(days=-day)).strftime("%Y%m%d")
            day += 1
            institutions = requests.get(
                f"https://www.twse.com.tw/fund/BFI82U?response=json&dayDate={today}"
            ).json()
            time.sleep(3)
            if institutions["stat"] == "OK":
                print(f"{today} checked")
                near_five_days_info[today] = institutions["data"]
        return near_five_days_info

    def _add_market_total(self):
        data = self._get_major_institutions()
        market_info = {}
        for k, v in data.items():
            if k not in market_info:
                market = requests.get(
                    f"https://www.twse.com.tw/exchangeReport/FMTQIK?response=json&date={k}"
                ).json()
                time.sleep(5)
                for info in market["data"]:
                    date = info[0].split("/")
                    date = f"{int(date[0])+1911}{date[1]}{date[2]}"
                    market_info[date] = int(info[2].replace(",", ""))
                data[k].append({"market_total": market_info[k]})
            else:
                data[k].append({"market_total": market_info[k]})
        return data

    def _major_ins_rank(self):
        near_five_days_rank = {}
        day = 0
        while len(near_five_days_rank) < 5:
            today = (datetime.now() + timedelta(days=-day)).strftime("%Y%m%d")
            day += 1
            data = requests.get(
                f"https://www.twse.com.tw/fund/T86?response=json&date={today}&selectType=ALL"
            ).json()
            time.sleep(3)
            if data["stat"] == "OK":
                print(f"{today} checked")
                sort_volume = sorted(
                    data["data"], key=lambda x: float(x[-1].replace(",", ""))
                )
                near_five_days_rank[today] = {
                    "buy10": sort_volume[-10::][::-1],
                    "sell10": sort_volume[:10],
                }
        return near_five_days_rank

    def major_ins_output(self):
        data = self._add_market_total()
        for k, v in data.items():
            print(k)
            status = "oversold" if v[4][3].startswith("-") else "overbought"
            print(f"{status} {v[4][3]}")
            buy = float(v[4][1].replace(",", ""))
            sell = float(v[4][2].replace(",", ""))
            total = v[-1]["market_total"]
            print(f"Proportion of Main trader {round((buy + sell) / total / 2 * 100, 2)} %")
            print("\n")
        return "DONE"

    def major_rank_output(self):
        rank = self._major_ins_rank()
        for k, v in rank.items():
            print(f"\n\n{k}")
            print("TOP 10 Overbought:")
            for stock_info in v["buy10"]:
                print(f"{stock_info[0]} {stock_info[1].strip()} : {stock_info[-1]}")
            print("\nOversold TOP 10:")
            for stock_info in v["sell10"]:
                print(f"{stock_info[0]} {stock_info[1].strip()} : {stock_info[-1]}")
        return "DONE"


class EXCEL_RAVEN:
    def filter_1(self, twenty_day_info):
        stocks = twenty_day_info
        qualified = []
        for k, v in stocks.items():
            if len(v["price"]) == 20:
                if (
                    (sum(v["price"][:5]) / 5) < (sum(v["price"][:10]) / 10)
                    and v["price"][0] > (sum(v["price"][:20]) / 20)
                    and (sum(v["volume"][:5]) / 5) > 1000
                    and v["price"][0] > (sum(v["price"][:5]) / 5)
                    and v["volume"][0] > v["volume"][1]
                ):
                    qualified.append((k, v["name"], f'Closing price for today : {v["price"][0]} $'))
        return qualified

    def filter_2(self, f1_qualified):
        headers = {
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36"
        }
        filter2_qualified = []
        for code, name, price in tqdm(f1_qualified):
            if len(code) == 6 and code.isdigit():
                pass
            else:
                time.sleep(1)
                text = requests.get(
                    f"https://tw.stock.yahoo.com/d/s/major_{code}.html", headers=headers
                ).text
                soup = BeautifulSoup(text, "lxml")
                try:
                    volume = soup.select("div.Fz\(24px\)")[0]
                    ratio = soup.select("div.Fz\(24px\)")[1]
                    if float(volume.string.replace(",", "")) > 0:
                        if float(ratio.string.replace("%", "")) >= 30:
                            filter2_qualified.append(
                                (
                                    code,
                                    name,
                                    price,
                                    f'Proportion of Main trader : {float(ratio.string.replace("%", ""))}%',
                                )
                            )
                except:
                    pass
        return filter2_qualified

    def filter_3(self, f1_qualified):
        filter3_qualified = []
        for code, name, price in tqdm(f1_qualified):
            if len(code) == 6 and code.isdigit():
                pass
            else:
                scr = self._get_scr(code)
                if scr >= 60:
                    filter3_qualified.append((code, name, price, f"SCR : {scr} %"))
        return filter3_qualified

    def filter_4(self, f1_qualified):
        top_50_stock = self._get_main_top50_stock()
        filter4_qualified = []
        for code, name, price in f1_qualified:
            if f"{code}{name}" in top_50_stock:
                filter4_qualified.append(
                    (
                        code,
                        name,
                        price,
                        f'Volume of oversold/overbought : {top_50_stock[f"{code}{name}"]["gap"]}',
                    )
                )
        return filter4_qualified

    def filter_5(self, f1_qualified):
        top_50_stock = self._get_foreign_top50_stock()
        filter5_qualified = []
        for code, name, price in f1_qualified:
            if f"{code}{name}" in top_50_stock:
                filter5_qualified.append(
                    (
                        code,
                        name,
                        price,
                        f'Volume of oversold/overbought : {top_50_stock[f"{code}{name}"]["gap"]}',
                    )
                )
        return filter5_qualified

    def _get_main_top50_stock(self):
        text = requests.get(
            "https://fubon-ebrokerdj.fbs.com.tw/z/zg/zg_F_0_2.djhtm"
        ).text
        soup = BeautifulSoup(text, "lxml")
        all_tr = soup.select("tr")[5:]
        stocks_info = {}
        column = ["price", "buy", "sell", "gap"]
        for tr in all_tr:
            if len(tr) > 1:
                stock_info = {}
                info = tr.select("td.t3n1")
                for idx in range(len(column)):
                    try:
                        stock_info[column[idx]] = info[idx].text.strip()
                    except:
                        pass
                stocks_info[
                    tr.select_one("td.t3t1").text.strip().replace(" ", "")
                ] = stock_info
        return stocks_info

    def _get_foreign_top50_stock(self):
        text = requests.get(
            "https://fubon-ebrokerdj.fbs.com.tw/z/zg/zg_D_0_2.djhtm"
        ).text
        soup = BeautifulSoup(text, "lxml")
        all_tr = soup.select("tr")[5:]
        stocks_info = {}
        column = ["price", "gap"]
        for tr in all_tr:
            if len(tr) > 1:
                stock_info = {}
                info = tr.select("td.t3n1")
                for idx in range(len(column)):
                    try:
                        stock_info[column[idx]] = info[idx].text.strip()
                    except:
                        pass
                stocks_info[
                    tr.select_one("td.t3t1").text.strip().replace(" ", "")
                ] = stock_info
        return stocks_info

    def _get_scr(self, code):
        try:
            text = requests.get(f"https://histock.tw/stock/large.aspx?no={code}").text
            time.sleep(2)
            soup = BeautifulSoup(text, "lxml")
            scr = pd.read_html(str(soup.select_one("table.tb-stock")))[0]["SCR"][0]
            return float(scr.replace("%", ""))
        except:
            return 0

    def excel_maker(self, twenty_day_info):
        df = pd.DataFrame()
        f1_qualified = self.filter_1(twenty_day_info)
        f2_qualified = self.filter_2(f1_qualified)
        f3_qualified = self.filter_3(f1_qualified)
        f4_qualified = self.filter_4(f1_qualified)
        f5_qualified = self.filter_5(f1_qualified)
        df["Type Filter"] = pd.Series(f1_qualified)
        df["Main Trader overbought& the proportion of Main Trader>=30%"] = pd.Series(f2_qualified)
        df["SCR>=60%"] = pd.Series(f3_qualified)
        df["TOP50 overbought for over 2 days"] = pd.Series(f4_qualified)
        df["TOP50 foreign overbought for over 2 days"] = pd.Series(f5_qualified)
        df.to_csv(
            f'{datetime.now().strftime("%Y%m%d")}stock_result.csv', encoding="utf_8_sig"
        )
        return "done"


if __name__ == "__main__":
    today = datetime.now().strftime("%Y%m%d")
    twenty_day_info = {}
    try:
        with open(f"{today}_20days_data.json") as json_file:
            twenty_day_info = json.load(json_file)
    except:
        pass

    while True:
        print("Ｗhat you want to do?\n 1: Type Filter\n 2: Chip Filter\n 3: excel maker\n 4: Download daily trading data\n 5: Finished Filter")
        system = input()
        if system == "1":
            raven = STOCK_RAVEN()
            if not twenty_day_info:
                twenty_day_info = raven._collect_stock()
            print(raven.qualified_stock(twenty_day_info))
        elif system == "2":
            raven = INS_RAVEN()
            print("1: Searching for overbought/oversold data for 5 days\n 2:Searching for TOP10 overbought/oversold stock in 5 days")
            choose = input()
            if choose == "1":
                print("Start Searching for overbought/oversold data for 5 days")
                raven.major_ins_output()
                print("Press any button to end")
                input()
            elif choose == "2":
                print("Start Searching for TOP10 overbought/oversold stock in 5 days")
                raven.major_rank_output()
                print("Press any button to end")
                input()
            else:
                print("Enter Error:No such function")
        elif system == "3":
            if not twenty_day_info:
                raven = STOCK_RAVEN()
                twenty_day_info = raven._collect_stock()
            raven = EXCEL_RAVEN()
            print(raven.excel_maker(twenty_day_info))
        elif system == "4":
            filename = "stock.csv"
            now = datetime.now().strftime("%Y_%m_%d")
            filename = now + '_' + filename
            stock_csv = str(Path('data', filename))

            stock_codes = read_stock_code(stock_csv)
            scrape_web(stock_codes)
        elif system == "5":
            Filter()
        else:
            print("Enter Error:No such function")

        
