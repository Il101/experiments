# Strategy Parameters

<cite>
**Referenced Files in This Document **   
- [market_scanner.py](file://breakout_bot/scanner/market_scanner.py)
- [signal_generator.py](file://breakout_bot/signals/signal_generator.py)
- [position_manager.py](file://breakout_bot/position/position_manager.py)
- [settings.py](file://breakout_bot/config/settings.py)
- [high_liquidity_top30.json](file://breakout_bot/config/presets/high_liquidity_top30.json)
- [smallcap_top_gainers.json](file://breakout_bot/config/presets/smallcap_top_gainers.json)
</cite>

## Table of Contents
1. [Liquidity Filters](#liquidity-filters)  
2. [Volatility Filters](#volatility-filters)  
3. [Signal Configuration](#signal-configuration)  
4. [Position Configuration](#position-configuration)  
5. [Scanner Configuration and Scoring](#scanner-configuration-and-scoring)  
6. [Execution Configuration](#execution-configuration)  
7. [Strategy Priority and Signal Generation](#strategy-priority-and-signal-generation)  
8. [Parameter Tuning and Backtesting Considerations](#parameter-tuning-and-backtesting-considerations)  
9. [Debugging Common Issues](#debugging-common-issues)

## Liquidity Filters

The `liquidity_filters` section defines minimum market quality thresholds to ensure sufficient trading depth, volume, and activity. These filters are applied in the `MarketFilter.apply_liquidity_filters()` method within `market_scanner.py`. Symbols failing any filter are excluded from further analysis.

Key parameters include:

- **min_24h_volume_usd**: Minimum 24-hour trading volume in USD. In `high_liquidity_top30.json`, this is set to 500,000,000 to focus on top-tier assets. In contrast, `smallcap_top_gainers.json` uses 50,000,000, allowing smaller-cap tokens with strong momentum.
- **min_depth_usd_0_5pct**: Minimum combined bid and ask depth within 0.5% of the current price. The high-liquidity preset requires $500,000, ensuring robust order book support, while the small-cap preset lowers this to $50,000 for less liquid markets.
- **max_spread_bps**: Maximum allowable bid-ask spread in basis points. Tight spreads (1.5 bps in high-liquidity vs. 3.0 bps in small-cap) reduce slippage risk.
- **min_trades_per_minute**: Ensures sufficient market activity. High-liquidity requires 15 trades per minute; small-cap accepts 3.0, acknowledging lower frequency in emerging tokens.

These filters prevent the system from engaging with illiquid or potentially manipulatable markets, directly influencing the candidate pool size and trade execution reliability.

**Section sources**
- [market_scanner.py](file://breakout_bot/scanner/market_scanner.py#L120-L170)
- [settings.py](file://breakout_bot/config/settings.py#L53-L69)
- [high_liquidity_top30.json](file://breakout_bot/config/presets/high_liquidity_top30.json#L14-L20)
- [smallcap_top_gainers.json](file://breakout_bot/config/presets/smallcap_top_gainers.json#L14-L20)

## Volatility Filters

The `volatility_filters` section ensures that selected symbols exhibit favorable volatility characteristics for breakout strategies. Implemented in `MarketFilter.apply_volatility_filters()`, these filters balance opportunity and noise.

Key parameters include:

- **atr_range_min/max**: Defines a range for the ATR-to-price ratio. The high-liquidity preset uses 0.006–0.035, targeting moderate volatility. The small-cap preset uses 0.015–0.08, capturing higher-volatility growth tokens.
- **volume_surge_1h_min/volume_surge_5m_min**: Minimum volume surge ratios over 1 hour and 5 minutes. Small-cap presets require higher surges (2.0x and 3.0x) to confirm strong momentum, while high-liquidity uses 1.3x and 1.8x, reflecting more stable volume patterns.
- **bb_width_percentile_max**: Caps Bollinger Band width percentile to avoid excessively volatile or stagnant conditions. High-liquidity uses 20.0, favoring tighter bands; small-cap allows up to 30.0 for more dynamic price action.

These filters help identify markets with meaningful price movements without excessive noise, improving signal quality.

**Section sources**
- [market_scanner.py](file://breakout_bot/scanner/market_scanner.py#L172-L195)
- [settings.py](file://breakout_bot/config/settings.py#L72-L96)
- [high_liquidity_top30.json](file://breakout_bot/config/presets/high_liquidity_top30.json#L21-L26)
- [smallcap_top_gainers.json](file://breakout_bot/config/presets/smallcap_top_gainers.json#L21-L26)

## Signal Configuration

The `signal_config` section governs the criteria for generating entry signals, implemented in `SignalValidator.validate_momentum_conditions()` and `validate_retest_conditions()` within `signal_generator.py`.

Key parameters include:

- **momentum_body_ratio_min**: Minimum ratio of candle body size to total range. High-liquidity uses 0.45, requiring a strong directional move. Small-cap uses 0.6, demanding even stronger conviction to filter out weak breakouts.
- **retest_pierce_tolerance**: Maximum allowed price penetration beyond a level during retest. Expressed as a multiplier of the level price, it controls how strictly the system enforces level integrity.
- **l2_imbalance_threshold**: Minimum absolute L2 order book imbalance to confirm buying or selling pressure. Small-cap uses a higher threshold (0.4) to ensure significant order flow, while high-liquidity uses 0.25.
- **vwap_gap_max_atr**: Maximum allowed gap between current price and VWAP, measured in ATR multiples. This ensures entries align with the volume-weighted trend.

These parameters define the "quality" of a breakout or retest, directly impacting signal confidence and win rate.

**Section sources**
- [signal_generator.py](file://breakout_bot/signals/signal_generator.py#L100-L150)
- [settings.py](file://breakout_bot/config/settings.py#L99-L116)
- [high_liquidity_top30.json](file://breakout_bot/config/presets/high_liquidity_top30.json#L27-L33)
- [smallcap_top_gainers.json](file://breakout_bot/config/presets/smallcap_top_gainers.json#L27-L33)

## Position Configuration

The `position_config` section dictates position management rules, handled by `PositionTracker` and `PositionManager` in `position_manager.py`.

Key parameters include:

- **tp1_r**: Take-profit level one, defined in R-multiples (risk units). Both presets use 1.0R, indicating a standard first profit target.
- **chandelier_atr_mult**: Multiplier for the Chandelier Exit trailing stop mechanism. High-liquidity uses 2.2, providing a tighter stop. Small-cap uses 2.8, allowing more room in volatile markets.
- **max_hold_time_hours**: Maximum time a position can remain open. High-liquidity allows 36 hours; small-cap limits to 18 hours, reflecting faster decay in momentum for smaller tokens.
- **add_on_enabled**: Enables adding to winning positions. High-liquidity enables this (0.4 max size); small-cap disables it, prioritizing capital preservation.

These settings automate risk management and profit-taking, crucial for consistent performance.

**Section sources**
- [position_manager.py](file://breakout_bot/position/position_manager.py#L200-L250)
- [settings.py](file://breakout_bot/config/settings.py#L118-L135)
- [high_liquidity_top30.json](file://breakout_bot/config/presets/high_liquidity_top30.json#L34-L40)
- [smallcap_top_gainers.json](file://breakout_bot/config/presets/smallcap_top_gainers.json#L34-L40)

## Scanner Configuration and Scoring

The `scanner_config` section controls the scanning process and candidate ranking via weighted scoring in `MarketScorer.calculate_score()`.

Key aspects include:

- **score_weights**: A dictionary assigning weights to different metrics (e.g., `vol_surge`, `oi_delta`). The sum of absolute weights should be approximately 1.0. High-liquidity equally weights volume surge, OI delta, ATR quality, and correlation (0.25 each), seeking balanced opportunities. Small-cap emphasizes volume surge (0.30) and includes `gainers_momentum` (0.05), tailoring the scan to its strategy.
- **top_n_by_volume**: Limits the initial scan to the top N symbols by 24h volume. High-liquidity scans the top 30; small-cap scans the top 200, casting a wider net for emerging gainers.

This configuration determines which candidates are considered and their relative priority, shaping the overall strategy profile.

**Section sources**
- [market_scanner.py](file://breakout_bot/scanner/market_scanner.py#L250-L300)
- [settings.py](file://breakout_bot/config/settings.py#L137-L155)
- [high_liquidity_top30.json](file://breakout_bot/config/presets/high_liquidity_top30.json#L41-L47)
- [smallcap_top_gainers.json](file://breakout_bot/config/presets/smallcap_top_gainers.json#L41-L47)

## Execution Configuration

The `execution_config` section manages order placement logic, particularly for large orders, to minimize market impact.

Key parameters include:

- **enable_twap**: Enables Time-Weighted Average Price slicing, breaking large orders into smaller pieces executed over time.
- **limit_offset_bps**: Sets the price offset in basis points for passive limit orders, helping capture maker fees.
- **twap_interval_seconds**: Controls the delay between TWAP slices, balancing speed and stealth.
- **spread_widen_bps**: Cancels execution if the market spread exceeds this value, preventing poor fills.

These settings optimize execution quality, especially critical for larger position sizes in the high-liquidity preset.

**Section sources**
- [settings.py](file://breakout_bot/config/settings.py#L157-L188)
- [high_liquidity_top30.json](file://breakout_bot/config/presets/high_liquidity_top30.json#L48-L58)
- [smallcap_top_gainers.json](file://breakout_bot/config/presets/smallcap_top_gainers.json#L48-L58)

## Strategy Priority and Signal Generation

The `strategy_priority` parameter directs the `SignalGenerator._generate_level_signal()` method to prioritize either 'momentum' or 'retest' strategies. If the primary strategy fails to generate a signal, it falls back to the secondary.

For example, `high_liquidity_top30.json` sets `strategy_priority: "momentum"`, seeking immediate breakouts in established trends. Conversely, `smallcap_top_gainers.json` uses `strategy_priority: "retest"`, waiting for pullbacks after breakouts, which can offer better risk-reward in fast-moving small-cap markets.

This choice fundamentally shapes the trading behavior, affecting entry timing, holding periods, and drawdown profiles.

**Section sources**
- [signal_generator.py](file://breakout_bot/signals/signal_generator.py#L500-L520)
- [high_liquidity_top30.json](file://breakout_bot/config/presets/high_liquidity_top30.json#L4)
- [smallcap_top_gainers.json](file://breakout_bot/config/presets/smallcap_top_gainers.json#L4)

## Parameter Tuning and Backtesting Considerations

Tuning parameters should align with market regimes:
- In trending markets, increase `volume_surge` thresholds to catch strong moves.
- In choppy markets, tighten `atr_range` and increase `body_ratio_min` to avoid false breakouts.
- For volatile altcoins, increase `chandelier_atr_mult` and decrease `max_hold_time_hours`.

Backtesting must validate:
- That `tp1_r` and `tp2_r` levels are realistically achievable.
- That liquidity filters prevent simulated fills in illiquid markets.
- That the `score_weights` produce a diversified and profitable candidate selection.

Always validate that the sum of TP sizes (`tp1_size_pct + tp2_size_pct`) does not exceed 1.0, as enforced by `validate_preset()`.

## Debugging Common Issues

Common issues and solutions:
- **No signals generated**: Check if `min_24h_volume_usd` or `atr_range` are too restrictive. Verify that `symbol_blacklist` isn't filtering all candidates.
- **Excessive false positives**: Increase `momentum_body_ratio_min` or `volume_surge` thresholds. Tighten `retest_pierce_tolerance`.
- **Poor execution fills**: Adjust `limit_offset_bps` or enable `iceberg` orders for large sizes.
- **Positions closed prematurely**: Increase `chandelier_atr_mult` or `max_hold_time_hours` for volatile assets.

Use diagnostic logs from `DiagnosticsCollector` to trace filter passes/fails and signal condition evaluations.