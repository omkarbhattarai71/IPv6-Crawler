import React, { useEffect, useMemo, useState } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Cell, ScatterChart, Scatter, ComposedChart
} from 'recharts';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

// Status indicator component
const StatusIndicator = ({ value, threshold = 50, label }) => {
  const status = value >= threshold ? 'success' : value >= threshold * 0.5 ? 'warning' : 'danger';
  return (
    <div className={`status-indicator ${status}`}>
      <div className="status-value">{value.toFixed(2)}%</div>
      <div className="status-label">{label}</div>
    </div>
  );
};

// Metric card component
const MetricCard = ({ title, value, subtitle, icon, trend, color = '#4e79a7' }) => {
  return (
    <div className="metric-card" style={{ borderLeftColor: color }}>
      <div className="metric-header">
        <h4>{title}</h4>
        {icon && <span className="metric-icon">{icon}</span>}
      </div>
      <div className="metric-value">{value.toLocaleString()}</div>
      {subtitle && <div className="metric-subtitle">{subtitle}</div>}
      {trend && (
        <div className={`trend ${trend > 0 ? 'positive' : 'negative'}`}>
          {trend > 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}%
        </div>
      )}
    </div>
  );
};

// Enhanced tooltip for charts
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="custom-tooltip">
        <p className="label">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} style={{ color: entry.color }}>
            {entry.name}: {entry.value.toLocaleString()}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

// Phase timeline component
const PhaseTimeline = ({ data, selectedPhase, onSelectPhase }) => {
  return (
    <div className="phase-timeline">
      <h5>Execution History</h5>
      <div className="timeline-container">
        {data.map((item, idx) => (
          <div
            key={idx}
            className={`timeline-item ${item.is_latest ? 'latest' : ''} ${selectedPhase?.phase === item.phase ? 'selected' : ''}`}
            onClick={() => onSelectPhase(item)}
            title={`Phase: ${item.phase}\nDate: ${item.date}`}
          >
            <div className="timeline-dot" />
            <div className="timeline-date">{item.date}</div>
            <div className="timeline-phase">{item.phase}</div>
            {item.is_latest && <div className="latest-badge">LATEST</div>}
          </div>
        ))}
      </div>
    </div>
  );
};

// Infrastructure breakdown card
const InfrastructureBreakdown = ({ data, totalSuccess }) => {
  const chartData = data.slice(0, 8).map(item => ({
    name: item.name.length > 20 ? item.name.substring(0, 20) + '...' : item.name,
    value: item.count,
    fullName: item.name
  }));

  const COLORS_INFRA = ['#4e79a7', '#59a14f', '#9c755f', '#f28e2b', '#e15759', '#76b7b2', '#bab0ac', '#8cd17d'];

  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    
    if (percent < 0.05) return null;
    
    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        className="pie-label"
      >
        {`${(percent * 100).toFixed(1)}%`}
      </text>
    );
  };

  return (
    <div className="infrastructure-card">
      <h5>Infrastructure Distribution (Top 8)</h5>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomLabel}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS_INFRA[index % COLORS_INFRA.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ backgroundColor: '#f9f9f9', border: '1px solid #ccc', borderRadius: '4px' }}
            formatter={(value) => `${value.toLocaleString()} (${((value / totalSuccess) * 100).toFixed(2)}%)`}
            labelFormatter={(label) => `Provider: ${label}`}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="infrastructure-list">
        {chartData.map((item, idx) => (
          <div key={idx} className="infra-item">
            <span className="infra-badge" style={{ backgroundColor: COLORS_INFRA[idx % COLORS_INFRA.length] }} />
            <span className="infra-name" title={item.fullName}>{item.name}</span>
            <span className="infra-value">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPhase, setSelectedPhase] = useState(null);
  const [query, setQuery] = useState('');
  const [sortKey, setSortKey] = useState('count');
  const [sortDir, setSortDir] = useState('desc');
  const [lastUpdate, setLastUpdate] = useState(null);

  // Fetch dashboard data
  const fetchDashboardData = async () => {
    try {
      // Add cache-busting parameter to force fresh data
      const response = await fetch(`/dashboard_data.json?t=${Date.now()}`);
      if (!response.ok) throw new Error(`Failed to fetch: ${response.status}`);
      
      const data = await response.json();
      
      // Clean up invalid data (convert boolean names to strings)
      if (data.top_infrastructure) {
        data.top_infrastructure = data.top_infrastructure.map(item => ({
          ...item,
          name: item.name === false ? 'No Response' : item.name === true ? 'Unknown' : String(item.name)
        }));
      }
      
      if (data.historical_data) {
        data.historical_data = data.historical_data.map(phase => ({
          ...phase,
          top_infrastructure: (phase.top_infrastructure || []).map(item => ({
            ...item,
            name: item.name === false ? 'No Response' : item.name === true ? 'Unknown' : String(item.name)
          }))
        }));
      }
      
      setDashboardData(data);
      setLastUpdate(new Date());
      setError(null);
      setLoading(false);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
      setError(err.message);
      setLoading(false);
    }
  };

  // Load data on mount and set up auto-refresh
  useEffect(() => {
    // Load immediately
    fetchDashboardData();

    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchDashboardData, 5000);

    return () => clearInterval(interval);
  }, []);

  // Initialize with latest phase when data loads
  useEffect(() => {
    if (dashboardData?.historical_data && dashboardData.historical_data.length > 0 && !selectedPhase) {
      const latest = dashboardData.historical_data.find(p => p.is_latest) || dashboardData.historical_data[0];
      setSelectedPhase(latest);
    }
  }, [dashboardData, selectedPhase]);

  const currentData = selectedPhase || dashboardData;
  const stats = currentData?.stats || dashboardData?.scan_stats;
  const infrastructure = currentData?.top_infrastructure || dashboardData?.top_infrastructure || [];

  // Calculate metrics
  const hitRate = stats.hit_rate_percentage || ((stats.success / stats.total) * 100);
  const failRate = 100 - hitRate;
  const successRatio = (stats.success / stats.total) * 100;

  // Trend calculation (comparing with previous phase)
  const trendHitRate = useMemo(() => {
    if (!dashboardData.historical_data || dashboardData.historical_data.length < 2) return 0;
    const sorted = [...dashboardData.historical_data].sort((a, b) => new Date(b.date) - new Date(a.date));
    const current = sorted[0];
    const previous = sorted[1];
    return ((current.stats.hit_rate_percentage - previous.stats.hit_rate_percentage) / previous.stats.hit_rate_percentage) * 100;
  }, []);

  // Prepare historical trend data
  const trendData = useMemo(() => {
    if (!dashboardData.historical_data) return [];
    return dashboardData.historical_data
      .slice()
      .sort((a, b) => new Date(a.date) - new Date(b.date))
      .map(item => ({
        date: item.date,
        phase: item.phase,
        hitRate: item.stats.hit_rate_percentage,
        success: item.stats.success,
        failed: item.stats.failed,
        total: item.stats.total
      }));
  }, []);

  // Success vs Failed comparison data
  const comparisonData = useMemo(() => {
    if (!dashboardData.historical_data) return [];
    return dashboardData.historical_data
      .slice()
      .sort((a, b) => new Date(a.date) - new Date(b.date))
      .map(item => ({
        phase: item.phase.substring(0, 8),
        Success: item.stats.success,
        Failed: item.stats.failed,
        total: item.stats.total
      }));
  }, []);

  // Filtered infrastructure data
  const filteredInfra = useMemo(() => {
    return infrastructure
      .filter(item => item.name.toLowerCase().includes(query.toLowerCase()))
      .sort((a, b) => {
        let cmp = 0;
        if (sortKey === 'name') cmp = a.name.localeCompare(b.name);
        else cmp = Number(a[sortKey]) - Number(b[sortKey]);
        return sortDir === 'asc' ? cmp : -cmp;
      });
  }, [infrastructure, query, sortKey, sortDir]);

  // Show loading state
  if (loading) {
    return (
      <div className="app-container">
        <div style={{ textAlign: 'center', padding: '40px', fontSize: '18px', color: '#666' }}>
          <div style={{ marginBottom: '20px' }}>📊 Loading Dashboard Data...</div>
          <div style={{ fontSize: '14px', color: '#999' }}>Fetching latest metrics from pipeline...</div>
        </div>
      </div>
    );
  }

  // Show error state
  if (error || !dashboardData) {
    return (
      <div className="app-container">
        <div style={{ textAlign: 'center', padding: '40px', fontSize: '18px', color: '#d32f2f' }}>
          <div style={{ marginBottom: '20px' }}>⚠️ Error Loading Dashboard</div>
          <div style={{ fontSize: '14px', color: '#999', marginBottom: '20px' }}>
            {error || 'Could not load dashboard data'}
          </div>
          <button
            onClick={fetchDashboardData}
            style={{
              padding: '10px 20px',
              backgroundColor: '#1976d2',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            🔄 Retry
          </button>
        </div>
      </div>
    );
  }

  // Guard against missing stats/infrastructure
  if (!stats || !infrastructure) {
    return (
      <div className="app-container">
        <div style={{ textAlign: 'center', padding: '40px', fontSize: '18px', color: '#ff9800' }}>
          <div>⏳ Waiting for Pipeline Data</div>
          <div style={{ fontSize: '14px', color: '#999', marginTop: '10px' }}>
            No data available yet. Pipeline may be running...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div>
            <h1>IPv6 Crawler Dashboard</h1>
            <p className="header-subtitle">Active IPv6 Prefix Analysis & Infrastructure Mapping</p>
          </div>
          <div className="header-meta">
            <span className="last-updated">
              Last Updated: {dashboardData?.last_updated 
                ? new Date(dashboardData.last_updated).toLocaleString()
                : 'Loading...'}
            </span>
            <span className="total-phases">
              Phases: {dashboardData?.total_phases || dashboardData?.historical_data?.length || 0}
            </span>
            <span style={{ fontSize: '12px', color: '#999', marginLeft: '20px' }}>
              🔄 Auto-refresh: {lastUpdate ? `${Math.floor((Date.now() - lastUpdate.getTime()) / 1000)}s ago` : 'pending'}
            </span>
          </div>
        </div>
      </header>

      <div className="app-body">
        {/* KPI Section */}
        <section className="kpi-section">
          <div className="kpi-grid">
            <MetricCard
              title="Total Scanned"
              value={stats.total}
              subtitle="IPv6 addresses scanned"
              icon="🎯"
              color="#4e79a7"
            />
            <MetricCard
              title="Success Count"
              value={stats.success}
              subtitle={`${successRatio.toFixed(2)}% successful`}
              icon="✓"
              color="#59a14f"
              trend={trendHitRate}
            />
            <MetricCard
              title="Failed Count"
              value={stats.failed}
              subtitle={`${failRate.toFixed(2)}% failed`}
              icon="✗"
              color="#e15759"
            />
            <MetricCard
              title="Hit Rate"
              value={hitRate}
              subtitle="Success percentage"
              icon="📊"
              color="#f28e2b"
              trend={trendHitRate}
            />
          </div>
        </section>

        {/* Status Indicators */}
        <section className="status-section">
          <h4>Performance Metrics</h4>
          <div className="status-grid">
            <StatusIndicator value={successRatio} threshold={75} label="Success Rate" />
            <StatusIndicator value={hitRate} threshold={50} label="Hit Rate" />
            <StatusIndicator value={Math.min(100, (stats.success / Math.max(1, stats.total)) * 100)} threshold={60} label="Efficiency" />
          </div>
        </section>

        {/* Phase Timeline */}
        {dashboardData.historical_data && dashboardData.historical_data.length > 0 && (
          <section className="timeline-section">
            <PhaseTimeline
              data={dashboardData.historical_data}
              selectedPhase={selectedPhase}
              onSelectPhase={setSelectedPhase}
            />
          </section>
        )}

        {/* Charts Grid */}
        <div className="charts-grid">
          {/* Hit Rate Trend */}
          {trendData.length > 0 && (
            <div className="chart-card">
              <h5>Hit Rate Trend</h5>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="colorHitRate" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f28e2b" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#f28e2b" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis dataKey="date" stroke="#666" />
                  <YAxis stroke="#666" />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="hitRate"
                    stroke="#f28e2b"
                    fillOpacity={1}
                    fill="url(#colorHitRate)"
                    name="Hit Rate (%)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Success vs Failed Comparison */}
          {comparisonData.length > 0 && (
            <div className="chart-card">
              <h5>Success vs Failed Comparison</h5>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={comparisonData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis dataKey="phase" stroke="#666" />
                  <YAxis stroke="#666" />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar dataKey="Success" fill="#59a14f" radius={[8, 8, 0, 0]} />
                  <Bar dataKey="Failed" fill="#e15759" radius={[8, 8, 0, 0]} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Infrastructure Distribution */}
          <div className="chart-card">
            <InfrastructureBreakdown data={infrastructure} totalSuccess={stats.success} />
          </div>

          {/* Top Infrastructure Providers */}
          <div className="chart-card">
            <h5>Top Infrastructure Providers</h5>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={infrastructure.slice(0, 10)}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 200 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                <XAxis type="number" stroke="#666" />
                <YAxis dataKey="name" type="category" width={190} tick={{ fontSize: 12 }} stroke="#666" />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" fill="#4e79a7" radius={[0, 8, 8, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Infrastructure Table */}
        <section className="table-section">
          <div className="table-header">
            <h4>All Infrastructure Providers</h4>
            <input
              type="text"
              placeholder="Search providers..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="search-input"
            />
          </div>

          <div className="table-controls">
            <div className="control-group">
              <label>Sort By:</label>
              <select value={sortKey} onChange={(e) => setSortKey(e.target.value)} className="control-select">
                <option value="name">Name</option>
                <option value="count">Count</option>
              </select>
            </div>
            <div className="control-group">
              <label>Direction:</label>
              <select value={sortDir} onChange={(e) => setSortDir(e.target.value)} className="control-select">
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </div>
          </div>

          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th onClick={() => { setSortKey('name'); setSortDir(sortDir === 'asc' && sortKey === 'name' ? 'desc' : 'asc'); }} className="sortable">
                    Provider Name {sortKey === 'name' && (sortDir === 'asc' ? '↑' : '↓')}
                  </th>
                  <th onClick={() => { setSortKey('count'); setSortDir(sortDir === 'asc' && sortKey === 'count' ? 'desc' : 'asc'); }} className="sortable">
                    Count {sortKey === 'count' && (sortDir === 'asc' ? '↑' : '↓')}
                  </th>
                  <th>Percentage</th>
                  <th>Share</th>
                </tr>
              </thead>
              <tbody>
                {filteredInfra.map((item, idx) => (
                  <tr key={idx} className={idx % 2 === 0 ? 'even' : 'odd'}>
                    <td className="provider-name" title={item.name}>{item.name}</td>
                    <td className="count-value">{item.count.toLocaleString()}</td>
                    <td className="percentage">{((item.count / stats.success) * 100).toFixed(3)}%</td>
                    <td>
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{ width: `${(item.count / stats.success) * 100}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="table-footer">
            <span className="result-count">Showing {filteredInfra.length} of {infrastructure.length} providers</span>
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer className="app-footer">
        <p>IPv6 Crawler Analytics | Powered by LightGBM ML Pipeline</p>
      </footer>
    </div>
  );
}

export default App;
