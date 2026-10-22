/* Pure pricing functions shared by the browser and Node regression tests. */
(function (root) {
  'use strict';
  // Reserve only the visit's duration at the highest catalog rate per minute.
  // A long alternative service contributes its rate, not its entire price.
  function maximumTimeCost(services, minutes) {
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > 1440 || !services.length) return null;
    if (services.some(function (s) {
      return !Number.isSafeInteger(s.price) || s.price < 0 ||
        !Number.isInteger(s.min) || s.min < 1 || s.min > 1440 ||
        !Number.isSafeInteger(s.price * minutes);
    })) return null;
    var peak = services.reduce(function (best, s) {
      return s.price / s.min > best.price / best.min ? s : best;
    });
    return Math.ceil(peak.price * minutes / peak.min);
  }
  function individualVisit(services, policy, selectedMaster, basePrice, minutes) {
    if (!policy || policy.mode !== 'maximum-time-rate' ||
        !Array.isArray(policy.masters) || !policy.masters.length ||
        new Set(policy.masters.map(function (m) { return m.id; })).size !== policy.masters.length ||
        !policy.masters.some(function (m) { return m.id === selectedMaster; }) ||
        !Number.isSafeInteger(basePrice) || basePrice < 0) return null;
    var breakdown = [], total = 0, estimated = false;
    for (var i = 0; i < policy.masters.length; i++) {
      var master = policy.masters[i];
      var available = services.filter(function (s) {
        return (s.master || 'venera') === master.id && s.cat !== 'men' &&
          (!s.status || s.status === 'published');
      });
      var maximum = maximumTimeCost(available, minutes);
      if (maximum === null) return null;
      estimated = estimated || available.some(function (s) { return !!s.priceStatus; });
      // The service price already pays the selected master's work.
      var surcharge = master.id === selectedMaster ? Math.max(0, maximum - basePrice) : maximum;
      total += surcharge;
      breakdown.push({ master: master.id, label: master.label, maximum: maximum, surcharge: surcharge });
    }
    return { surcharge: total, total: basePrice + total, breakdown: breakdown, estimated: estimated };
  }
  var api = { maximumTimeCost: maximumTimeCost, individualVisit: individualVisit };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.BookingPricing = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
