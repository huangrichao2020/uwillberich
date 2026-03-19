# Data Sources

Use primary and official sources first when the conclusion depends on policy, rates, or geopolitics.

## Official And Primary Sources

| Source | Use | Notes |
|---|---|---|
| `pbc.gov.cn` | `LPR`, PBOC guidance, domestic policy timing | Use exact release dates and times |
| `federalreserve.gov` | FOMC statements and projections | Use official statement pages for exact wording |
| `bankofengland.co.uk` | BOE policy decisions | Useful when global rates affect risk appetite |
| `snb.ch` | SNB policy decisions | Secondary global rates input |
| `apnews.com` / `reuters.com` | Geopolitics, oil, fast macro news | Use for timely cross-market context |

## Market Data Endpoints In This Skill

### Tencent Quote Snapshot

- Endpoint: `https://qt.gtimg.cn/q=...`
- Use: liquid stock watchlists
- Encoding: `GBK`
- Key parsed fields:
  - name
  - code
  - price
  - prior close
  - open
  - high
  - low
  - absolute change
  - percent change
  - amount
  - timestamp

### Eastmoney Index Snapshot

- Endpoint: `https://push2.eastmoney.com/api/qt/ulist.np/get`
- Use: main index levels and simple breadth
- Default symbols:
  - `1.000001` Shanghai Composite
  - `0.399001` Shenzhen Component
  - `0.399006` ChiNext
  - `1.000300` CSI 300
  - `1.000688` STAR 50
  - `0.899050` Beijing 50

### Eastmoney Sector Breadth

- Endpoint: `https://push2.eastmoney.com/api/qt/clist/get`
- Use: strongest and weakest sectors on the day
- The skill defaults to concept-board ranking with the common Eastmoney parameters already set in the script.

## Practical Notes

- These public endpoints may throttle or change.
- Use scripts for fast snapshots, not for blindly trusting a single source.
- If the user asks for the latest or today’s view, verify the unstable facts live before drawing conclusions.
