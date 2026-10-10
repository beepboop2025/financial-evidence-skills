# Finance research integrations: 11 October 2026

The [forward research kit](https://github.com/beepboop2025/financial-evidence-skills/tree/main/integrations/finance-research) adds
usable examples for LangChain/LangGraph, CrewAI, a local TradingAgents analyst,
a QuantConnect custom-data candidate, and Hummingbot/Freqtrade operators.
It reuses the existing public evidence client and framework adapters.

The key behavior is explicit knowledge time. `event_time` retains the economic
observation's original date and precision. `available_at` is the completion of
this local capture, never a claim about original publisher availability.
Historical backtest mode and decisions before capture time are refused. A
QuantConnect numerical record uses capture time as its timeline index; older
economic dates remain separate metadata.

The kit preserves nulls, source fields, units, source status, rights labels,
transport diagnostics and pagination. Missing/restricted values remain in the
retained packet and appear with reasons in the numerical-export receipt. A
complete bounded request keeps `coverage_complete=false`; it does not establish
complete market coverage. Hashes detect changes to retained content and do not
establish independent timing or rights approval.

The [validation record](https://github.com/beepboop2025/financial-evidence-skills/blob/main/integrations/finance-research/validation.json)
separates actual framework runtime checks, the synthetic public API probe, and
platform work still needing a native environment. The companion does not read
broker credentials or create execution hooks. No independent-user, recurring
use, marketplace acceptance or revenue claim follows from these checks.

The QuantConnect route remains subject to its [vendor qualification](https://www.quantconnect.com/docs/v2/cloud-platform/datasets/vendors).
This kit supplies forward-capture mechanics; it does not create original-vintage
history, one-year delivery evidence or a channel-specific data licence.
