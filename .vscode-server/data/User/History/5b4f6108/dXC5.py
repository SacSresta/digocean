from data import ForexData
from Technicals import Indicator
import time
import pandas as pd
import logging
import os
from logger import LogWrapper
from Trademanager import Trademanager

def save_all_candle_data(candle_data_all):
    new_data_df = pd.DataFrame(candle_data_all)
    try:
        if os.path.exists('candle_data_all.csv'):
            existing_data_df = pd.read_csv('candle_data_all.csv')
            combined_data_df = pd.concat([existing_data_df, new_data_df], ignore_index=True)
        else:
            combined_data_df = new_data_df

        combined_data_df.to_csv('candle_data_all.csv', index=False)
        logging.info("Candle data saved to candle_data_all.csv.")
    except PermissionError as e:
        logging.error(f"Permission error saving candle data to CSV: {e}")
        alternative_filename = 'candle_data_backup.csv'
        combined_data_df.to_csv(alternative_filename, index=False)
        logging.info(f"Backup candle data saved to {alternative_filename}.")

def save_candle_data(candle_data, pair, directory='data'):
    # Create the directory if it does not exist
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # Construct the file path
    file_path = os.path.join(directory, f'{pair}.csv')
    backup_file_path = os.path.join(directory, f'{pair}_candle_data_backup.csv')

    new_data_df = pd.DataFrame(candle_data)
    try:
        if os.path.exists(file_path):
            existing_data_df = pd.read_csv(file_path)
            combined_data_df = pd.concat([existing_data_df, new_data_df], ignore_index=True)
        else:
            combined_data_df = new_data_df

        combined_data_df.to_csv(file_path, index=False)
        logging.info(f"Candle data saved to {file_path}.")
    except PermissionError as e:
        logging.error(f"Permission error saving candle data to CSV: {e}")
        combined_data_df.to_csv(backup_file_path, index=False)
        logging.info(f"Backup candle data saved to {backup_file_path}.")

def main():
    instrument = [
        "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CAD", "USD_CHF", "NZD_USD",
        "EUR_GBP", "EUR_AUD", "EUR_NZD", "EUR_JPY", "EUR_CHF", "EUR_CAD",
        "GBP_AUD", "GBP_NZD", "GBP_JPY", "GBP_CAD", "GBP_CHF",
        "AUD_NZD", "AUD_JPY", "AUD_CHF", "AUD_CAD",
        "NZD_JPY", "NZD_CHF", "NZD_CAD",
        "CAD_JPY", "CAD_CHF", "CHF_JPY"
    ]  
    candle_data_all = []# Initialize an empty list to store the last candle data
    try:
        while True:
            for pair in instrument:
                candle_data = []
                log = LogWrapper(name = pair)
                last_candle = Trademanager().fetch_and_process(pair,granularity="D")
                if last_candle is not None:
                    log.logger.info(f"Last candle data: {last_candle}")
                    candle_data_all.append(last_candle.to_dict())
                    if 'SIGNAL' in last_candle and last_candle['SIGNAL']:
                        print(f"Signal for {pair} generated running check.")
                        result = ForexData().run_check(pair)
                        if isinstance(result,tuple):
                            check,matching_pair = result
                            print(f"matching pairs found here :{matching_pair}")
                            current_trades = ForexData().running_trades()
                            for running_pair in matching_pair:
                                trades_to_close = current_trades[current_trades['instrument'] == running_pair]
                                for index, trade in trades_to_close.iterrows():
                                    log.logger.info(f"Order for id: {trade['id']} for {trade['currentUnits']} units of pair {running_pair} is getting closed as it was opened before.")
                                    print(f"Closing trade for id:{trade['id']},pair:{trade['instrument']}")
                                    ForexData().close_trade(trade_id= trade['id'], units=abs(int(trade['currentUnits'])))
                        side = last_candle['Position']
                        price_type = 'bid' if side == "buy" else 'ask'
                        last_candle = Trademanager().fetch_and_process(instrument=pair, price_type=price_type, granularity="D")
                        pipvalue = Trademanager().pip_size(last_candle)
                        print(pipvalue)
                        position_size = round(Trademanager().position_size_calculator(stop_loss=pipvalue*1.5))
                        unit = position_size * last_candle['Close'] if pair != "EUR_USD" else position_size
                        print(unit)
                        SL = last_candle['SL']
                        TP = last_candle['TP']
                        # Append the last_candle to the candle_data list
                        candle_data.append(last_candle.to_dict())
                        order_response = ForexData().create_order(instrument=pair, units=round(unit), order_type="MARKET", side=side, stop_loss=SL, take_profit= TP)
                        if order_response is not None:
                            log.logger.info(f"Order placed for {pair}. Side: {side}, Time: {last_candle['Time']}, Details: {order_response}, Units: {unit}")
                            print(f"Order placed for {pair}. Side: {side}, Time: {last_candle['Time']},Details:{order_response}")
                            save_candle_data(candle_data,pair)
            time.sleep(86400)
    except KeyboardInterrupt:
        logging.info("Script interrupted. Saving collected candle data.")
        save_all_candle_data(candle_data_all)
if __name__ == "__main__":
    print("Bot started.")
    main()
    print("Bot stopped.")