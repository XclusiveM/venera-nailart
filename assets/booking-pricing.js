/* Pure pricing functions shared by the browser and Node regression tests. */
(function (root) {
  'use strict';
  // Maximise complete bookings starting inside the blocked interval.
  // The last booking may finish after it; its entire price is counted.
  function maximumBookings(services, minutes) {
    if (!Number.isInteger(minutes) || minutes < 1 || minutes > 1440 || !services.length) return null;
    if (services.some(function (s) {
      return !Number.isSafeInteger(s.price) || s.price < 0 ||
        !Number.isInteger(s.min) || s.min < 1 || s.min > 1440;
    })) return null;
    var best = new Array(minutes).fill(-1), maximum = 0;
    best[0] = 0;
    for (var elapsed = 0; elapsed < minutes; elapsed++) {
      if (best[elapsed] < 0) continue;
      services.forEach(function (s) {
        var revenue = best[elapsed] + s.price, end = elapsed + s.min;
        maximum = Math.max(maximum, revenue);
        if (end < minutes) best[end] = Math.max(best[end], revenue);
      });
    }
    return maximum;
  }
  function individualVisit(services, policy, selectedMaster, basePrice, minutes) {
    if (!policy || policy.mode !== 'maximum-overlapping-bookings' ||
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
      var maximum = maximumBookings(available, minutes);
      if (maximum === null) return null;
      estimated = estimated || available.some(function (s) { return !!s.priceStatus; });
      // The service price already pays the selected master's work.
      var surcharge = master.id === selectedMaster ? Math.max(0, maximum - basePrice) : maximum;
      total += surcharge;
      breakdown.push({ master: master.id, label: master.label, maximum: maximum, surcharge: surcharge });
    }
    return { surcharge: total, total: basePrice + total, breakdown: breakdown, estimated: estimated };
  }
  var api = { maximumBookings: maximumBookings, individualVisit: individualVisit };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.BookingPricing = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
