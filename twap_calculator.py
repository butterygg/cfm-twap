import json
import sys
from operator import itemgetter

def calculate_twaps(file_path, csms_path, output_path="twap-results.json"):
    # Load TWAP data
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Load CSM data
    with open(csms_path, 'r') as f:
        csm_data = json.load(f)
    
    # Create token mapping for each pair
    token_map = {}
    for market in csm_data['data']['conditionalScalarMarkets']:
        pair_address = market['pair']['id'].lower()
        token_map[pair_address] = {
            'token0': market['pair']['token0']['id'].lower(),
            'token1': market['pair']['token1']['id'].lower(),
            'longToken': market['longToken']['id'].lower(),
            'shortToken': market['shortToken']['id'].lower(),
            'outcomeIndex': market['outcomeIndex']
        }
    
    # Initialize result structure
    result = {
        "startBlock": data["startBlock"],
        "startBlockTime": None,
        "endBlock": data["endBlock"],
        "endBlockTime": None,
        "pairs": {}
    }
    
    # For tracking top 5 pools by pTwap
    top_pools = []
    
    for pair_address, pair_data in data['pairs'].items():
        pair_address_lower = pair_address.lower()
        
        # Set block times if not set yet
        if result["startBlockTime"] is None:
            result["startBlockTime"] = pair_data['start']['blockTimestamp']
        if result["endBlockTime"] is None:
            result["endBlockTime"] = pair_data['end']['blockTimestamp']
        
        # Extract timestamps
        start_timestamp = pair_data['start']['blockTimestamp']
        start_timestamp_last = pair_data['start']['blockTimestampLast']
        end_timestamp = pair_data['end']['blockTimestamp']
        end_timestamp_last = pair_data['end']['blockTimestampLast']
        
        # Extract cumulative prices
        price0_cumulative_start = pair_data['start']['price0Cumulative']
        price1_cumulative_start = pair_data['start']['price1Cumulative']
        price0_cumulative_end = pair_data['end']['price0Cumulative']
        price1_cumulative_end = pair_data['end']['price1Cumulative']
        
        # Time discrepancies
        start_discrepancy = start_timestamp - start_timestamp_last
        end_discrepancy = end_timestamp - end_timestamp_last
        
        # Extract reserve values
        reserve0_start = pair_data['start']['reserve0']
        reserve1_start = pair_data['start']['reserve1']
        reserve0_end = pair_data['end']['reserve0']
        reserve1_end = pair_data['end']['reserve1']
        
        # Extrapolate prices at start
        price0_extrapolated_start = price0_cumulative_start
        price1_extrapolated_start = price1_cumulative_start
        
        if start_discrepancy > 0:
            # Calculate instant price at start (reserve1/reserve0 and reserve0/reserve1)
            Q112 = 2**112
            instant_price0_start = (reserve1_start * Q112) // reserve0_start
            instant_price1_start = (reserve0_start * Q112) // reserve1_start
            
            # Extrapolate
            price0_extrapolated_start += instant_price0_start * start_discrepancy
            price1_extrapolated_start += instant_price1_start * start_discrepancy
        
        # Extrapolate prices at end
        price0_extrapolated_end = price0_cumulative_end
        price1_extrapolated_end = price1_cumulative_end
        
        if end_discrepancy > 0:
            # Calculate instant price at end
            Q112 = 2**112
            instant_price0_end = (reserve1_end * Q112) // reserve0_end
            instant_price1_end = (reserve0_end * Q112) // reserve1_end
            
            # Extrapolate
            price0_extrapolated_end += instant_price0_end * end_discrepancy
            price1_extrapolated_end += instant_price1_end * end_discrepancy
        
        # Calculate time elapsed between desired timepoints
        time_elapsed_extrapolated = end_timestamp - start_timestamp
        
        # Calculate TWAPs
        Q112 = 2**112
        
        # Extrapolated TWAPs
        if time_elapsed_extrapolated > 0:
            twap0_extrapolated = (price0_extrapolated_end - price0_extrapolated_start) / time_elapsed_extrapolated / Q112
            twap1_extrapolated = (price1_extrapolated_end - price1_extrapolated_start) / time_elapsed_extrapolated / Q112
        else:
            twap0_extrapolated = twap1_extrapolated = 0
        
        # Map TWAPs to short/long tokens
        pair_output = {
            "price0Twap": twap0_extrapolated,
            "price1Twap": twap1_extrapolated
        }
        
        # Add token mapping if available
        if pair_address_lower in token_map:
            tokens = token_map[pair_address_lower]
            pair_output["outcomeIndex"] = tokens['outcomeIndex']
            
            # Determine which price (0 or 1) corresponds to short/long
            if tokens['token0'].lower() == tokens['shortToken'].lower():
                # token0 is short, token1 is long
                pair_output["priceShortTwap"] = twap0_extrapolated
                pair_output["priceLongTwap"] = twap1_extrapolated
            else:
                # token0 is long, token1 is short
                pair_output["priceShortTwap"] = twap1_extrapolated
                pair_output["priceLongTwap"] = twap0_extrapolated
            
            # Calculate pTwap = priceLongTwap/(1+priceLongTwap)
            price_long_twap = pair_output["priceLongTwap"]
            p_twap = price_long_twap / (1 + price_long_twap)
            pair_output["pTwap"] = p_twap
            
            # Add to top pools list for sorting later
            top_pools.append({
                "address": pair_address,
                "outcomeIndex": tokens['outcomeIndex'],
                "pTwap": p_twap
            })
        
        # Add to result
        result["pairs"][pair_address] = pair_output
    
    # Write to output file
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Results written to {output_path}")
    
    # Print top 5 pools by pTwap
    top_pools.sort(key=itemgetter('pTwap'), reverse=True)
    print("\nTop 5 pools by pTwap:")
    print("---------------------")
    print("Rank | Outcome Index |    pTwap    | Pool Address")
    print("----|--------------|------------|------------------")
    
    for i, pool in enumerate(top_pools[:5], 1):
        print(f" {i:2d} | {pool['outcomeIndex']:12d} | {pool['pTwap']:.8f} | {pool['address']}")
    
    return result

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python twap_calculator.py <prices_json> <csms_json> [output_json]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    csms_path = sys.argv[2]
    
    output_path = "twap-results.json"
    if len(sys.argv) > 3:
        output_path = sys.argv[3]
    
    calculate_twaps(file_path, csms_path, output_path)
