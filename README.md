# howto

```sh
export TODAY=$(date +'%Y-%m-%d')
```

On the subgraph, get

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
CSM_JSON=csm-list.json END_BLOCK=… START_BLOCK=… forge script script/FetchCumulativePrices.s.sol:FetchCumulativePrices
```

Copy the resulting file in this folder's `./data/$TODAY`.

In this folder, run

```sh
python twap_calculator.py data/$TODAY/cumulative-prices.json data/$TODAY/csm-list.json data/$TODAY/raw-twaps.json
```

enjoy🥤
