# Required Imports
import matplotlib
import pandas as pd
from copy import copy
from chapter1 import calculate_stats
from chapter3 import standardDeviation
from chapter4 import (
    get_data_dict,
    calculate_variable_standard_deviation_for_risk_targeting_from_dict,
    calculate_position_series_given_variable_risk_for_dict,
    create_fx_series_given_adjusted_prices_dict,
    aggregate_returns,
)

matplotlib.use("TkAgg")

# Define the function to calculate positions with a trend filter applied at the dictionary level.
# This function loops through each instrument in the dictionary and applies the trend filter to the positions.
def calculate_position_dict_with_trend_filter_applied(adjusted_prices_dict: dict, average_position_contracts_dict: dict) -> dict:
    # Function body here
    list_of_instruments = list(adjusted_prices_dict.keys())
    position_dict_with_trend_filter = dict(
        [
            (
                instrument_code,
                calculate_position_with_trend_filter_applied(
                    adjusted_prices_dict[instrument_code],
                    average_position_contracts_dict[instrument_code],
                ),
            )
            for position_dict_with_trend_filter in list_of_instruments
        ]
    )
    return position_dict_with_trend_filter
# Define the function to apply trend filter on positions at the series level.
# This function takes an instrument's adjusted prices and average positions to filter positions based on trend.
def calculate_position_with_trend_filter_applied(adjusted_price: pd.Series, average_position: pd.Series) -> pd.Series:
    # Function body here
    filtered_position = copy(average_position)
    ewmac_values = ewmac(adjusted_price)
    bearish = ewmac_values < 0
    filtered_position[bearish] = 0
    return filtered_position

# Define the function to compute EWMAC (Exponentially Weighted Moving Average Crossover) values.
# This is used for trend filtering. A positive value indicates bullish trend, negative indicates bearish trend.
def ewmac(adjusted_price: pd.Series, fast_span=16, slow_span=64) -> pd.Series:
    # Function body here
    slow_ewma = adjusted_price.ewm(span=slow_span, min_periods=2).mean()
    fast_ewma = adjusted_price.ewm(span=fast_span, min_periods=2).mean()
    return fast_ewma - slow_ewma

# Define the function to calculate percentage returns at the dictionary level after accounting for costs.
# This function loops through each instrument and calculates percentage returns.
def calculate_perc_returns_for_dict_with_costs(position_contracts_dict: dict, adjusted_prices: dict, multipliers: dict, fx_series: dict, capital: float, cost_per_contract_dict: dict, std_dev_dict: dict) -> dict:
    # Function body here
    perc_returns_dict = dict(
        [
            (
                instrument_code,
                calculate_perc_returns_with_costs(
                    position_contracts_held=position_contracts_dict[instrument_code],
                    adjusted_price=adjusted_prices[instrument_code],
                    multiplier=multipliers[instrument_code],
                    fx_series=fx_series[instrument_code],
                    capital_required=capital,
                    cost_per_contract=cost_per_contract_dict[instrument_code],
                    stdev_series=std_dev_dict[instrument_code],
                ),
            )
            for instrument_code in position_contracts_dict.keys()
        ]
    )
    return perc_returns_dict
# Define the function to calculate percentage returns at the series level after accounting for costs.
# This includes costs such as contract costs, and adjusts for currency effects.
def calculate_perc_returns_with_costs(position_contracts_held: pd.Series, adjusted_price: pd.Series, fx_series: pd.Series, stdev_series: standardDeviation, multiplier: float, capital_required: float, cost_per_contract: float) -> pd.Series:
    # Function body here
    # Calculate the return based on the change in price and positions held from the previous day.
    precost_return_price_points = (adjusted_price - adjusted_price.shift(1)) * position_contracts_held.shift(1)

    # Convert price returns to monetary returns using the contract multiplier.
    precost_return_instrument_currency = precost_return_price_points * multiplier

    # Calculate the costs deflated by the instrument's volatility.
    historic_costs = calculate_costs_deflated_for_vol(stddev_series=stdev_series, cost_per_contract=cost_per_contract,
                                                      position_contracts_held=position_contracts_held)

    # Align the dates of cost data with the returns data.
    historic_costs_aligned = historic_costs.reindex(precost_return_instrument_currency.index, method="ffill")

    # Subtract the cost from the return to get the net return in the instrument's currency.
    return_instrument_currency = (precost_return_instrument_currency - historic_costs_aligned)

    # Align the dates of the foreign exchange data with the returns data.
    fx_series_aligned = fx_series.reindex(return_instrument_currency.index, method="ffill")

    # Convert the return to the base currency using the foreign exchange rate.
    return_base_currency = return_instrument_currency * fx_series_aligned

    # Convert the monetary return to a percentage of the total capital.
    perc_return = return_base_currency / capital_required
    return perc_return


# Define the function to calculate historical costs after adjusting for volatility.
# Costs are deflated based on the standard deviation of price.
def calculate_costs_deflated_for_vol(stddev_series: standardDeviation, cost_per_contract: float, position_contracts_held: pd.Series) -> pd.Series:
    # Function body here
    # Round positions to whole numbers and compute the change in positions to calculate trades.
    round_position_contracts_held = position_contracts_held.round()
    position_change = (round_position_contracts_held - round_position_contracts_held.shift(1))
    abs_trades = position_change.abs()

    # Adjust the per-contract cost for volatility.
    historic_cost_per_contract = calculate_deflated_costs(stddev_series=stddev_series,
                                                          cost_per_contract=cost_per_contract)

    # Align the dates of cost data with the trades data.
    historic_cost_per_contract_aligned = historic_cost_per_contract.reindex(abs_trades.index, method="ffill")

    # Multiply the number of trades by the cost per trade to get the total cost.
    historic_costs = abs_trades * historic_cost_per_contract_aligned
    return historic_costs

# Define the function to deflate costs based on standard deviation.
# This adjusts the cost per contract based on the volatility of price.
def calculate_deflated_costs(stddev_series: standardDeviation, cost_per_contract: float) -> pd.Series:
    # Function body here
    stdev_daily_price = stddev_series.daily_risk_price_terms()
    final_stdev = stdev_daily_price.iloc[-1]

    # Deflate the cost based on how current volatility compares to the final volatility.
    cost_deflator = stdev_daily_price / final_stdev
    historic_cost_per_contract = cost_per_contract * cost_deflator
    return historic_cost_per_contract


# Main Execution Block
if __name__ == "__main__":
    pass
    # Step-by-step comments guiding through the main block's flow.

    # 1. Fetch the adjusted prices and current prices for each instrument.
    adjusted_prices_dict, current_prices_dict = get_data_dict()
    # Function: get_data_dict
    # Result: Dictionary of adjusted prices and current prices.

    # 2. Create the foreign exchange series based on adjusted prices.
    multipliers = dict(sp500=5, us10=1000)
    risk_target_tau = 0.2
    # Function: create_fx_series_given_adjusted_prices_dict
    # Result: Dictionary of foreign exchange series.
    fx_series_dict = create_fx_series_given_adjusted_prices_dict(adjusted_prices_dict)
    capital = 1000000
    idm = 1.5
    instrument_weights = dict(sp500=0.5, us10=0.5)
    cost_per_contract_dict = dict(sp500=0.875, us10=5)

    # 3. Calculate the standard deviation for risk targeting.
    # Function: calculate_variable_standard_deviation_for_risk_targeting_from_dict
    # Result: Dictionary of standard deviations.
    std_dev_dict = calculate_variable_standard_deviation_for_risk_targeting_from_dict(
        adjusted_prices=adjusted_prices_dict, current_prices=current_prices_dict, use_perc_returns=True,
        annualise_stdev=True)

    # 4. Calculate the average position of contracts given the variable risk.
    # Function: calculate_position_series_given_variable_risk_for_dict
    # Result: Dictionary of average position of contracts.
    average_position_contracts_dict = calculate_position_series_given_variable_risk_for_dict(
        capital=capital, risk_target_tau=risk_target_tau, idm=idm, weights=instrument_weights,
        std_dev_dict=std_dev_dict, fx_series_dict=fx_series_dict, multipliers=multipliers)

    # 5. Apply trend filter to the positions.
    # Function: calculate_position_dict_with_trend_filter_applied
    # Result: Dictionary of positions after trend filter is applied.
    position_contracts_dict = calculate_position_dict_with_trend_filter_applied(
        adjusted_prices_dict=adjusted_prices_dict, average_position_contracts_dict=average_position_contracts_dict)

    # 6. Calculate percentage returns after considering costs.
    # Function: calculate_perc_returns_for_dict_with_costs
    # Result: Dictionary of percentage returns.
    perc_return_dict = calculate_perc_returns_for_dict_with_costs(
        position_contracts_dict=position_contracts_dict, fx_series=fx_series_dict, multipliers=multipliers,
        capital=capital, adjusted_prices=adjusted_prices_dict, cost_per_contract_dict=cost_per_contract_dict,
        std_dev_dict=std_dev_dict)


    # 7. Aggregate the returns.
    # Function: aggregate_returns
    # Result: Aggregated return series.
    perc_return_agg = aggregate_returns(perc_return_dict)

    # 8. Calculate stats for a specific instrument (e.g., "sp500") and for aggregated returns.
    # Functions: calculate_stats
    # Result: Dictionary of statistical measures.
    stats_dict = calculate_stats(perc_return_dict["sp500"])
    stats_dict2 = calculate_stats(perc_return_agg)

    # 9. Convert the stats dictionary to a dataframe for better visualization and print.
    stats_df = pd.DataFrame(list(stats_dict.items()), columns=['Identifier', 'Value'])
    stats_df2 = pd.DataFrame(list(stats_dict2.items()), columns=['Identifier', 'Value'])

    print(stats_df, "\n")
    print(stats_df2, "\n")
