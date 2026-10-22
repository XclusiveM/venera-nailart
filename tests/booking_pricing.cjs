const assert = require('node:assert/strict');
const { maximumTimeCost, individualVisit } = require('../assets/booking-pricing.js');
const services = [
  { id: 'short', master: 'venera', cat: 'mani', price: 1000, min: 30 },
  { id: 'complex', master: 'venera', cat: 'mani', price: 3000, min: 90 },
  { id: 'other', master: 'julia', cat: 'mani', price: 2000, min: 60 },
  { id: 'hidden', master: 'julia', cat: 'mani', price: 99999, min: 1, status: 'hidden' },
  { id: 'men', master: 'venera', cat: 'men', price: null, min: null }
];
const policy = { mode: 'maximum-time-rate', masters: [
  { id: 'venera', label: 'Венера' }, { id: 'julia', label: 'Юлия' }
] };
let quote = individualVisit(services, policy, 'venera', 1000, 30);
assert.equal(quote.total, 2000); // Only 30 minutes per master, not two full appointments.
assert.equal(quote.surcharge, 1000);
assert.equal(quote.breakdown[0].surcharge, 0); // Selected service already pays Venera's time.
quote = individualVisit(services, policy, 'venera', 9000, 30);
assert.equal(quote.surcharge, 1000); // A high base price never erases the other master's time.
assert.equal(individualVisit(services, policy, 'julia', 2000, 60).total, 4000);
assert.equal(individualVisit(services, policy, 'venera', 1000, null), null);
assert.equal(individualVisit(services, policy, 'missing', 1000, 30), null);
assert.equal(individualVisit([], policy, 'venera', 1000, 30), null);
assert.equal(individualVisit(services, {...policy, mode:'maximum-overlapping-bookings'}, 'venera', 1000, 30), null);
assert.equal(maximumTimeCost([{ price: null, min: 30 }], 30), null);
assert.equal(maximumTimeCost([{ price: 1000, min: 0 }], 30), null);
assert.equal(maximumTimeCost(services.slice(0, 2), 1441), null);
assert.equal(maximumTimeCost([{price:Number.MAX_SAFE_INTEGER,min:30}], 2), null);
assert.equal(maximumTimeCost([{price:3000,min:90}], 45), 1500); // No full complex charged for 45 minutes.
assert.equal(maximumTimeCost([{price:600,min:30},{price:3000,min:150}], 45), 900); // Splitting a visit cannot inflate its rate.
assert.equal(maximumTimeCost([{price:100,min:3}], 1), 34); // Round only to a whole ruble.
const catalog = require('../data/services.json');
quote = individualVisit(catalog.services, catalog.individualVisit, 'venera', 1700, 45);
assert.equal(quote.total, 3825);
assert.equal(quote.surcharge, 2125);
assert.deepEqual(quote.breakdown.map(x=>x.maximum), [2475,1350]);
assert.deepEqual(quote.breakdown.map(x=>x.surcharge), [775,1350]);
assert.equal(quote.estimated, true);
console.log('OK: duration-based maximum rates, no double billing, long services, invalid inputs and catalog quote');
