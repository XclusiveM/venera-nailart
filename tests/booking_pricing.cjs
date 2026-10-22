const assert = require('node:assert/strict');
const { maximumBookings, individualVisit } = require('../assets/booking-pricing.js');
const services = [
  { id: 'short', master: 'venera', cat: 'mani', price: 1000, min: 30 },
  { id: 'complex', master: 'venera', cat: 'mani', price: 3000, min: 90 },
  { id: 'other', master: 'julia', cat: 'mani', price: 2000, min: 60 },
  { id: 'hidden', master: 'julia', cat: 'mani', price: 99999, min: 1, status: 'hidden' },
  { id: 'men', master: 'venera', cat: 'men', price: null, min: null }
];
const policy = { mode: 'maximum-overlapping-bookings', masters: [
  { id: 'venera', label: 'Венера' }, { id: 'julia', label: 'Юлия' }
] };
let quote = individualVisit(services, policy, 'venera', 1000, 30);
assert.equal(quote.total, 5000); // Full complex + other master's booking.
assert.equal(quote.surcharge, 4000); // Chosen service isn't billed twice.
assert.equal(quote.breakdown[0].surcharge, 2000);
quote = individualVisit(services, policy, 'venera', 9000, 30);
assert.equal(quote.surcharge, 2000); // Never discount a costly selected visit.
assert.equal(individualVisit(services, policy, 'julia', 2000, 60).total, 6000);
assert.equal(individualVisit(services, policy, 'venera', 1000, null), null);
assert.equal(individualVisit(services, policy, 'missing', 1000, 30), null);
assert.equal(individualVisit([], policy, 'venera', 1000, 30), null);
assert.equal(maximumBookings([{ price: null, min: 30 }], 30), null);
assert.equal(maximumBookings([{ price: 1000, min: 0 }], 30), null);
assert.equal(maximumBookings(services.slice(0, 2), 1441), null);
assert.equal(maximumBookings(services.slice(0, 2), 90), 5000);
assert.equal(maximumBookings(services.slice(0, 2), 91), 6000);
// Compare the optimiser with exhaustive schedules on small independent fixtures.
function brute(items, remaining) {
  return Math.max(...items.map(s => s.price + (s.min < remaining ? brute(items, remaining - s.min) : 0)));
}
for (let minutes = 1; minutes <= 12; minutes++) {
  const items = [{ price: 7, min: 3 }, { price: 12, min: 5 }, { price: 20, min: 8 }];
  assert.equal(maximumBookings(items, minutes), brute(items, minutes));
}
console.log('OK: individual visit pricing, unknown inputs, boundaries and exhaustive comparison');
