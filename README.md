# compute TWAPs for Butter's CFMs

## rationale

This calculation is directly based on Uniswap v2's cumulative prices and their [docs](https://docs.uniswap.org/contracts/v2/concepts/core-concepts/oracles)' recommended approach for computing TWAPs.

Instead of relying on Solidity libraries that are harder to maintain and knowing we can afford to forego a bit of decimal precision, we take the following approach:

1. fetch data from Uniswap v2 pairs, including reserves and cumulative prices
2. compute locally the TWAPs, including the extrapolation routine
3. finally, produce a `pTwap` value, which represents the value of Long (UP) tokens in terms of their collateral token.

The final output `pTwap` is calculated based on the invariant `Long + Short = 1`, stemming from Long and Short tokens being complementary outcomes.  
Given the computed `twap` of the Long/Short token ratio, we have:

```
pTwap = twap / (1 + twap)
```

The script outputs a list of all `pTwap` values, enabling Butter’s CFMs to apply their decision rule by comparing projects' Conditional Scalar Market forecasts.

## install

Install the [cfm-v1](https://github.com/butterygg/cfm-v1) smart contracts forge project then the current repository.

```sh
gh repo clone butterygg/cfm-v1
cd cfm-v1
forge soldeer install

cd ..
gh repo clone butterygg/twap
```

## howto

### 1. fetch

```sh
export TODAY=$(date +'%Y-%m-%d')
```

On the [cfm-v1-unichain-mainnet](https://thegraph.com/explorer/subgraphs/ApyDeZakPYAEkCu8neFQ9pMaPmAwSLbpZZfBhDW5F18r?view=Query&chain=arbitrum-one) subgraph, get

```graphql
{
  conditionalScalarMarkets (where: {decisionMarket_: {id: $cfmId}}) {
    longToken{id}
    shortToken{id}
    invalidToken{id}
    outcomeIndex
    pair{id}
  }
```

Copy the resulting file in this folder's `./data/$TODAY` and in `cfm-v1`.

Pick the start and end block numbers that correspond to the TWAP period.

In `cfm-v1`, run

```sh
CSM_JSON=csm-list.json END_BLOCK=… START_BLOCK=… forge script script/FetchCumulativePrices.s.sol
```

Copy the resulting file in this folder's `./data/$TODAY`.

## 2 & 3. compute TWAP and calculate `pTwap`

In this folder, run

```sh
python twap_calculator.py data/$TODAY/cumulative-prices.json data/$TODAY/csm-list.json data/$TODAY/raw-twaps.json
```

Now you can observe results in the `raw-twaps.json` file, or just read stdout:

```
Top 5 pools by pTwap:
---------------------
Rank| Outcome Index|    pTwap   | Pool Address
----|--------------|------------|------------------
  1 |           15 | 0.59401587 | 0x9d16947a1924F735EC86CA4C11b3e28cE65b436e
  2 |           17 | 0.48530209 | 0x23b04c96C0bb8c223d13C6962c4aCF954412E77B
  3 |            1 | 0.47911263 | 0xED69FC5B54757cbeE0136C516a22E406AFd5Fa11
  4 |            0 | 0.44333008 | 0x7A0986507e4836CF234d42d049682A1D8A57a1F6
  5 |           12 | 0.41237347 | 0xCb6B543857DaBb2308Cc9DE4d09d5cbcEDed80c2
```

enjoy🥤
