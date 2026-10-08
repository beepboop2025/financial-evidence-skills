// Browser-only execution walkthrough. All market/account inputs are synthetic.
export class PaperSandbox {
  constructor(clock = () => Date.now()) {
    this.clock = clock;
    this.cash = 100000;
    this.btc = 0;
    this.stopped = false;
    this.assessments = new Map();
    this.orders = new Map();
    this.sequence = 0;
    this.quote = {bid:60000, ask:60010};
  }
  assess(intent, side, notional) {
    if (typeof intent !== 'string' || !/^[a-zA-Z0-9-]{1,80}$/.test(intent)
        || !['buy','sell'].includes(side) || !Number.isFinite(notional)
        || notional <= 0 || notional > 1000) throw new Error('Choose buy or sell and a size above $0 up to $1,000.');
    const existing = this.assessments.get(intent);
    if (existing) {
      if (existing.side !== side || existing.notional !== notional) throw new Error('This intent already belongs to another proposal.');
      return structuredClone(existing);
    }
    if (this.assessments.size >= 100) throw new Error('This walkthrough retains 100 intents. Export the journal, then reload to start a new simulation.');
    const price = side === 'buy' ? this.quote.ask : this.quote.bid;
    const quantity = notional / price;
    if (side === 'buy' && notional > this.cash || side === 'sell' && quantity > this.btc) throw new Error('The simulated account has insufficient cash or BTC. Short selling is disabled.');
    const value = {intent, side, notional, price, quantity, expires_at:this.clock()+60000, sequence:this.sequence, mode:'simulation'};
    this.assessments.set(intent, value);
    return structuredClone(value);
  }
  submit(intent, {timeout = false} = {}) {
    if (this.orders.has(intent)) return structuredClone(this.orders.get(intent));
    if (this.stopped) throw new Error('STOP is active. New submissions are disabled.');
    if ([...this.orders.values()].some(order => order.state === 'uncertain')) throw new Error('Reconcile the uncertain order before creating another submission.');
    const assessment = this.assessments.get(intent);
    if (!assessment || this.clock() >= assessment.expires_at || this.clock() < assessment.expires_at - 60000 || assessment.sequence !== this.sequence) throw new Error('Assessment missing, expired, or superseded by an account change. Preview a new decision.');
    if (assessment.price !== (assessment.side === 'buy' ? this.quote.ask : this.quote.bid)) throw new Error('The synthetic quote changed. Preview a new decision.');
    if (assessment.side === 'buy' && assessment.notional > this.cash || assessment.side === 'sell' && assessment.quantity > this.btc) throw new Error('The simulated account cannot cover this order.');
    // Reserve the stable intent before the simulated broker accepts the order.
    const order = {...assessment, state: timeout ? 'uncertain' : 'filled', broker_order_id:`simulation-${this.orders.size+1}`, simulated:true};
    this.orders.set(intent, order);
    this.cash += assessment.side === 'buy' ? -assessment.notional : assessment.notional;
    this.btc += assessment.side === 'buy' ? assessment.quantity : -assessment.quantity;
    this.sequence++;
    return structuredClone(order);
  }
  reconcile(intent) {
    const order = this.orders.get(intent);
    if (!order) throw new Error('No submitted order has that intent.');
    order.state = 'filled';
    return structuredClone(order);
  }
  snapshot() {
    return {schema:'liquilens.execution-walkthrough.v1', mode:'simulation',
      market_data:'synthetic', broker_contacted:false, cash:this.cash, btc:this.btc,
      stopped:this.stopped, orders:structuredClone([...this.orders.values()]),
      customer_or_revenue_evidence:false};
  }
}
