# Daily demand model — daily-ridge-1

## Intended use
Evaluate one-day-ahead unit-sales prediction for **one product** from daily history. The model learns coefficients; the pricing cockpit remains an assumption calculator and operational recommendations remain deterministic. No learned model can publish or override a price. No LLM subscription, API key or external inference service is needed.

## Input contract
`DemandHistory` accepts 180–1,095 consecutive daily rows for one product: date, gross EUR own price, gross EUR competitor benchmark, units sold, promotion flag and full-day availability. Zero-sales days are explicit. Missing/duplicate dates, future sales, nonfinite money, extra fields and invalid units are rejected. The declared origin is supplied by the uploader, not independently authenticated.

The price, competitor benchmark and promotion must be known at the start of the sales period. Supplying end-of-day values creates leakage that the software cannot detect. Prices need a consistent tax/delivery basis, product variant and channel across the entire series. Do not pool products, channels or return-adjusted negative sales into this contract. No customer-level data is needed.

## Method
Numpy implements standardized ridge regression on `log1p(units)`, with an unpenalized intercept. Features are log own price, log competitor price, promotion, linear age of the observed series, weekday sine/cosine, and log of the previous seven days' mean sales. Training residuals supply a smearing correction when transforming predictions back to unit counts. Values are bounded to the input contract's 0–100,000 range as a numerical safeguard, not a stock cap.

The objective is squared log-target error plus alpha times squared standardized feature weights. Feature means/scales are fitted on training data only. This small implementation keeps the estimator inspectable; it is not a novel algorithm. Raw learned coefficients are included for reproducibility and **must not be presented as causal price elasticity**.

## Temporal protocol
Seven initial days supply lag features. The final 84 days contain three fixed 28-day blocks: validation, calibration and test. Earlier usable days train the model. Validation selects alpha from 0.1, 1, 10, 100 using MAE. The model is then fitted on training plus validation; calibration and test do not update weights. Calibration residuals determine an empirical nominal 80% absolute-error band. Test evaluates the frozen model against a seven-day mean and a same-weekday-last-week predictor.

One-day-ahead test predictions use previously observed test sales in lag features, as they become available. This is **not** a forecast of all 28 days made at one origin. Test errors never select alpha. Test price extrapolation is reported. Daily prices/promotion are treated as known inputs; this is conditional prediction, not joint forecasting of future market prices.

Days without full-day stock are excluded as targets: constrained sales do not measure full demand. Their observed sales remain in lag features. Missing-not-at-random availability and stockout-induced lags remain limitations. At least 56 usable training days and 14 usable days in each final block are required. Zero-sales training abstains; zero-volume WAPE is null.

## Evidence and failure mode
Run `python -m scripts.evaluate_demand` for all five fixed seeds and both stable and unseen-shock regimes. Each result includes dataset SHA-256, version, split dates, validation trials, MAE/RMSE/WAPE/bias, interval coverage, coefficients and every holdout prediction. The generator is separate from the fitted function and includes omitted effects, noise and stock constraints. It is still synthetic and favors some assumed relationships; success does not validate a real market.

The default synthetic case improves over simple baselines. An unseen demand contraction exposes poor adaptation and reduced interval coverage. Both outcomes are visible in the UI. Empirical bands lack guaranteed coverage under temporal dependence, changing conditions or the excluded-stockout selection process. The baseline-comparison badge is descriptive of this test, not authorization to deploy.

## Privacy and operation
Uploads are evaluated in server memory and are not persisted by the application or sent to an external AI provider. They pass through the configured hosting service. Request bodies are limited to 2 MB in the web host, UI uploads to 1 MB, and training to two concurrent evaluations. Logs should not be configured to capture request bodies. Use only data you are permitted to process. Public demo mode is not a production merchant-data environment.

## Promotion criteria still to establish
Obtain permissioned real data, validate timestamp availability and SKU comparability, evaluate several rolling windows and product/store segments, compare against appropriate baselines, and quantify error/coverage under shocks. Define thresholds with a merchant **before** the pilot. Price optimization requires separate causal evidence or a controlled intervention; forecasting accuracy alone cannot justify a price change or a profit-uplift claim.

Method references: [scikit-learn temporal cross-validation](https://sklearn.org/stable/modules/cross_validation.html#time-series-split) and [leakage precautions](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage). These inform the evaluation protocol; scikit-learn is not a runtime dependency.
