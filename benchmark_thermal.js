const { performance } = require('perf_hooks');

// Mock data generation: 500 records across 10 zones (50 records per zone)
const zoneMap = {};
for (let i = 0; i < 10; i++) {
  const zone_id = `ZONE-${String(i).padStart(3, '0')}`;
  zoneMap[zone_id] = Array.from({ length: 50 }, () => 60 + Math.random() * 30);
}

function unoptimizedMapping(zoneMap) {
  return Object.entries(zoneMap).map(([zone_id, temps]) => ({
    zone_id,
    avg_temp:   temps.reduce((a, b) => a + b, 0) / temps.length,
    peak_temp:  Math.max(...temps),
    node_count: temps.length,
    status: Math.max(...temps) >= 85 ? 'critical' : Math.max(...temps) >= 78 ? 'hot' : Math.max(...temps) >= 70 ? 'warm' : 'nominal',
  }));
}

function optimizedMapping(zoneMap) {
  return Object.entries(zoneMap).map(([zone_id, temps]) => {
    const peak_temp = Math.max(...temps);
    return {
      zone_id,
      avg_temp:   temps.reduce((a, b) => a + b, 0) / temps.length,
      peak_temp,
      node_count: temps.length,
      status: peak_temp >= 85 ? 'critical' : peak_temp >= 78 ? 'hot' : peak_temp >= 70 ? 'warm' : 'nominal',
    };
  });
}

const iterations = 100000;

console.log(`Running benchmark with ${iterations} iterations...`);

// Warm-up
unoptimizedMapping(zoneMap);
optimizedMapping(zoneMap);

const startUnoptimized = performance.now();
for (let i = 0; i < iterations; i++) {
  unoptimizedMapping(zoneMap);
}
const endUnoptimized = performance.now();

const startOptimized = performance.now();
for (let i = 0; i < iterations; i++) {
  optimizedMapping(zoneMap);
}
const endOptimized = performance.now();

const timeUnoptimized = endUnoptimized - startUnoptimized;
const timeOptimized = endOptimized - startOptimized;

console.log(`Unoptimized total time: ${timeUnoptimized.toFixed(2)}ms`);
console.log(`Optimized total time: ${timeOptimized.toFixed(2)}ms`);
console.log(`Improvement: ${(((timeUnoptimized - timeOptimized) / timeUnoptimized) * 100).toFixed(2)}%`);
