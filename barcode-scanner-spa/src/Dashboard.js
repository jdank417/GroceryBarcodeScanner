// src/Dashboard.js
import React, { useEffect, useState } from 'react';
import Chart from 'chart.js/auto';
import moment from 'moment';

const Dashboard = () => {
  const [metrics, setMetrics] = useState({
    lookup_success_total: 0,
    lookup_failure_total: 0,
    barcode_scan_failure_total: 0
  });
  const [chartData, setChartData] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch('/api/historical?event_type=lookup_success&group_by=hour').then(r => r.json()),
      fetch('/api/historical?event_type=lookup_failure&group_by=hour').then(r => r.json()),
      fetch('/api/historical?event_type=barcode_scan_failure&group_by=hour').then(r => r.json())
    ]).then(([successData, lookupFailData, barcodeFailData]) => {
      // Create a set of all unique time labels
      const timeSet = new Set();
      successData.forEach(item => timeSet.add(item.hour));
      lookupFailData.forEach(item => timeSet.add(item.hour));
      barcodeFailData.forEach(item => timeSet.add(item.hour));
      const times = Array.from(timeSet).sort();

      const buildCounts = (data) => {
        const map = {};
        data.forEach(item => { map[item.hour] = item.count; });
        return times.map(time => map[time] || 0);
      };

      setChartData({
        labels: times,
        datasets: [
          {
            label: 'Successful Lookups',
            data: buildCounts(successData),
            backgroundColor: 'rgba(0, 128, 0, 0.7)'
          },
          {
            label: 'Lookup Failures',
            data: buildCounts(lookupFailData),
            backgroundColor: 'rgba(255, 0, 0, 0.7)'
          },
          {
            label: 'Barcode Decode Failures',
            data: buildCounts(barcodeFailData),
            backgroundColor: 'rgba(255, 255, 0, 0.7)'
          }
        ]
      });
    }).catch(error => console.error('Error fetching historical data:', error));

    // Optionally, update immediate metrics (this example uses static numbers)
    setMetrics({
      lookup_success_total: 123,
      lookup_failure_total: 45,
      barcode_scan_failure_total: 6
    });
  }, []);

  useEffect(() => {
    if (chartData) {
      const ctx = document.getElementById('combinedBarChart').getContext('2d');
      new Chart(ctx, {
        type: 'bar',
        data: chartData,
        options: {
          responsive: true,
          scales: {
            x: {
              title: { display: true, text: 'Date & Time' }
            },
            y: {
              beginAtZero: true,
              title: { display: true, text: 'Count' }
            }
          },
          plugins: {
            tooltip: {
              callbacks: {
                title: (tooltipItems) => moment(tooltipItems[0].label).format('MMM D, h:mm A'),
                label: (tooltipItem) => `Count: ${tooltipItem.parsed.y}`
              }
            }
          }
        }
      });
    }
  }, [chartData]);

  return (
    <main style={{ margin: '40px' }}>
      <h1 style={{ textAlign: 'center' }}>Application Metrics Dashboard</h1>
      <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: '2rem' }}>
        <div>
          <h5>Successful Lookups</h5>
          <p style={{ fontSize: '2rem', textAlign: 'center' }}>{metrics.lookup_success_total}</p>
        </div>
        <div>
          <h5>Lookup Failures</h5>
          <p style={{ fontSize: '2rem', textAlign: 'center' }}>{metrics.lookup_failure_total}</p>
        </div>
        <div>
          <h5>Barcode Decode Failures</h5>
          <p style={{ fontSize: '2rem', textAlign: 'center' }}>{metrics.barcode_scan_failure_total}</p>
        </div>
      </div>
      <div style={{ maxWidth: '900px', margin: '0 auto' }}>
        <canvas id="combinedBarChart"></canvas>
      </div>
    </main>
  );
};

export default Dashboard;
