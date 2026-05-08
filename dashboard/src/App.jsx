import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Cell, ScatterChart, Scatter, ComposedChart, RadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, Radar
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

// Port Reachability Analysis Component
const PortReachabilityChart = ({ portStats }) => {
  if (!portStats || Object.keys(portStats).length === 0) return null;

  const portNameMap = {
    'icmp': 'ICMP',
    'tcp80': 'TCP 80 (HTTP)',
    'tcp443': 'TCP 443 (HTTPS)',
    'tcp8080': 'TCP 8080',
    'tcp8443': 'TCP 8443',
    'udp53': 'UDP 53 (DNS)'
  };

  const data = Object.entries(portStats)
    .map(([port, stats]) => ({
      name: portNameMap[port] || port.toUpperCase(),
      shortName: port.toUpperCase(),
      percentage: stats.percentage,
      responsive: stats.responsive,
      protocol: port
    }))
    .sort((a, b) => b.percentage - a.percentage);

  const COLORS = ['#4e79a7', '#59a14f', '#f28e2b', '#e15759', '#76b7b2', '#bab0ac'];

  return (
    <div className="chart-container">
      <h5>🌐 Port Reachability Analysis</h5>
      <p className="section-subtitle">Count of IPs responding on each protocol (TRUE = responsive)</p>
      <ResponsiveContainer width="100%" height={350}>
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 80 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis 
            dataKey="name" 
            angle={-45} 
            textAnchor="end" 
            height={100}
            interval={0}
            tick={{ fontSize: 12 }}
          />
          <YAxis 
            label={{ value: 'Responsive IPs', angle: -90, position: 'insideLeft' }}
            yAxisId="left"
          />
          <YAxis 
            orientation="right"
            yAxisId="right"
            label={{ value: 'Response Rate (%)', angle: 90, position: 'insideRight' }}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#f9f9f9', border: '1px solid #ccc', borderRadius: '4px' }}
            formatter={(value, name) => {
              if (name === 'percentage') return [`${value.toFixed(2)}%`, 'Response Rate'];
              if (name === 'responsive') return [value.toLocaleString(), 'Responsive IPs'];
              return [value, name];
            }}
            labelFormatter={(label) => `${label} (${data.find(d => d.name === label)?.protocol})`}
          />
          <Legend />
          <Bar yAxisId="left" dataKey="responsive" fill="#4e79a7" radius={[8, 8, 0, 0]} name="Responsive IPs">
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Bar>
          <Line 
            yAxisId="right"
            type="monotone" 
            dataKey="percentage" 
            stroke="#f28e2b" 
            strokeWidth={2} 
            dot={{ r: 5 }}
            name="Response Rate (%)"
          />
        </BarChart>
      </ResponsiveContainer>
      
      {/* Protocol Statistics Table */}
      <div style={{ marginTop: '30px', backgroundColor: '#f9f9f9', borderRadius: '8px', padding: '15px' }}>
        <h6 style={{ marginBottom: '15px', color: '#333', fontWeight: 600 }}>Protocol Summary</h6>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
          {data.map((item, idx) => (
            <div 
              key={idx} 
              style={{
                padding: '15px',
                backgroundColor: '#fff',
                borderLeft: `4px solid ${COLORS[idx % COLORS.length]}`,
                borderRadius: '4px',
                boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
              }}
            >
              <div style={{ fontSize: '11px', color: '#999', textTransform: 'uppercase', marginBottom: '4px' }}>
                {item.shortName}
              </div>
              <div style={{ fontSize: '20px', fontWeight: 'bold', color: COLORS[idx % COLORS.length], marginBottom: '4px' }}>
                {item.responsive.toLocaleString()}
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                {item.percentage.toFixed(1)}% responsive
              </div>
              <div style={{ fontSize: '11px', color: '#999', marginTop: '4px' }}>
                {item.name}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Status Distribution Component
const StatusDistributionChart = ({ statusData }) => {
  if (!statusData || Object.keys(statusData).length === 0) return null;

  const data = Object.entries(statusData).map(([status, info]) => ({
    name: status.charAt(0).toUpperCase() + status.slice(1),
    value: info.count,
    percentage: info.percentage
  }));

  const COLORS_STATUS = ['#59a14f', '#e15759', '#f28e2b', '#4e79a7', '#76b7b2'];

  return (
    <div className="chart-container">
      <h5>📊 Status Distribution</h5>
      <p className="section-subtitle">Breakdown of response statuses</p>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ percentage }) => `${(percentage * 100).toFixed(1)}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS_STATUS[index % COLORS_STATUS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ backgroundColor: '#f9f9f9', border: '1px solid #ccc' }}
            formatter={(value, name, props) => [
              `${value} (${((value / data.reduce((sum, item) => sum + item.value, 0)) * 100).toFixed(2)}%)`,
              props.payload.name
            ]}
          />
        </PieChart>
      </ResponsiveContainer>
      <div style={{ marginTop: '20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px' }}>
        {data.map((item, idx) => (
          <div key={idx} style={{
            padding: '12px',
            backgroundColor: '#f5f5f5',
            borderLeft: `4px solid ${COLORS_STATUS[idx % COLORS_STATUS.length]}`,
            borderRadius: '4px'
          }}>
            <div style={{ fontSize: '12px', color: '#666' }}>{item.name}</div>
            <div style={{ fontSize: '18px', fontWeight: 'bold', color: COLORS_STATUS[idx % COLORS_STATUS.length] }}>
              {item.value.toLocaleString()}
            </div>
            <div style={{ fontSize: '11px', color: '#999' }}>{item.percentage.toFixed(1)}%</div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Multi-Port Analysis Component
const MultiPortAnalysisChart = ({ multiPortData }) => {
  if (!multiPortData || multiPortData.length === 0) return null;

  const data = multiPortData.sort((a, b) => a.ports - b.ports);

  return (
    <div className="chart-container">
      <h5>🔌 Multi-Port Analysis</h5>
      <p className="section-subtitle">How many IPs respond to multiple ports</p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis dataKey="ports" label={{ value: 'Number of Ports', position: 'insideBottomRight', offset: -5 }} />
          <YAxis label={{ value: 'IP Count', angle: -90, position: 'insideLeft' }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#f9f9f9', border: '1px solid #ccc' }}
            formatter={(value, name) => [
              value.toLocaleString(),
              name === 'count' ? 'IPs' : name
            ]}
          />
          <Bar dataKey="count" fill="#76b7b2" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// Temporal Trends Component
const TemporalTrendsChart = ({ scanHistory }) => {
  if (!scanHistory || scanHistory.length < 2) return null;

  const data = scanHistory
    .sort((a, b) => new Date(a.date) - new Date(b.date))
    .map(scan => ({
      date: new Date(scan.date).toLocaleDateString(),
      phase: scan.phase,
      responseRate: scan.response_rate !== undefined ? scan.response_rate : scan.success_rate || 0,
      responsiveIPs: scan.responsive_ips || 0,
      totalIPs: scan.total_ips || 0
    }));

  return (
    <div className="chart-container">
      <h5>📈 Temporal Trends</h5>
      <p className="section-subtitle">Response rates over time across scans</p>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis dataKey="date" angle={-45} textAnchor="end" height={80} />
          <YAxis yAxisId="left" label={{ value: 'Response Rate (%)', angle: -90, position: 'insideLeft' }} />
          <YAxis yAxisId="right" orientation="right" label={{ value: 'IP Count', angle: 90, position: 'insideRight' }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#f9f9f9', border: '1px solid #ccc' }}
            formatter={(value, name) => {
              if (name === 'responseRate') return [`${value.toFixed(2)}%`, 'Response Rate'];
              if (name === 'responsiveIPs') return [value.toLocaleString(), 'Responsive IPs'];
              return [value.toLocaleString(), name];
            }}
          />
          <Legend />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="responseRate"
            stroke="#4e79a7"
            strokeWidth={2}
            dot={{ r: 4 }}
            name="Response Rate"
          />
          <Area
            yAxisId="right"
            type="monotone"
            dataKey="responsiveIPs"
            fill="#f28e2b"
            stroke="#f28e2b"
            opacity={0.3}
            name="Responsive IPs"
          />
        </ComposedChart>
      </ResponsiveContainer>
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
  const [isHeaderHidden, setIsHeaderHidden] = useState(false);
  const lastScrollYRef = useRef(0);

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

      if (data.latest_scan?.top_infrastructure) {
        data.latest_scan.top_infrastructure = data.latest_scan.top_infrastructure.map(item => ({
          ...item,
          name: item.name === false ? 'No Response' : item.name === true ? 'Unknown' : String(item.name)
        }));
      }

      if (Array.isArray(data.scan_history)) {
        data.scan_history = data.scan_history.map(phase => ({
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

  // Compact header on scroll, hide while scrolling down
  useEffect(() => {
    lastScrollYRef.current = window.scrollY;
    let ticking = false;

    const onScroll = () => {
      const currentScrollY = window.scrollY;
      const delta = currentScrollY - lastScrollYRef.current;

      if (!ticking) {
        window.requestAnimationFrame(() => {
          const hideOn = currentScrollY > 120 && delta > 6;
          const hideOff = currentScrollY < 80 || delta < -6;

          setIsHeaderHidden(prev => {
            const next = prev ? !hideOff : hideOn;
            return next === prev ? prev : next;
          });

          lastScrollYRef.current = currentScrollY;
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  // Initialize with latest phase when data loads
  useEffect(() => {
    const scans = dashboardData?.scan_history || [];
    if (scans.length > 0 && !selectedPhase) {
      const latest = dashboardData?.latest_scan || scans.find(p => p.is_latest) || scans[scans.length - 1];
      setSelectedPhase(latest);
    }
  }, [dashboardData, selectedPhase]);

  const scans = useMemo(() => dashboardData?.scan_history || [], [dashboardData]);
  const currentScan = selectedPhase || dashboardData?.latest_scan || scans.find(p => p.is_latest) || scans[scans.length - 1];

  const totalIps = currentScan?.total_ips || dashboardData?.summary?.total_ips_scanned || 0;
  const responsiveIps = currentScan?.responsive_ips ?? dashboardData?.summary?.responsive_ips ?? 0;
  const successfulIps = currentScan?.successful_ips ?? dashboardData?.summary?.successful_ips ?? 0;
  const responseRate = currentScan?.response_rate ?? dashboardData?.summary?.response_rate_percentage ?? (totalIps ? (responsiveIps / totalIps) * 100 : 0);
  const successRate = currentScan?.success_rate ?? dashboardData?.summary?.success_rate_percentage ?? (totalIps ? (successfulIps / totalIps) * 100 : 0);

  // Optional legacy infrastructure (only render if present)
  const infrastructure = currentScan?.top_infrastructure || dashboardData?.top_infrastructure || [];
  const hasInfra = Array.isArray(infrastructure) && infrastructure.length > 0;
  const infraTotal = currentScan?.stats?.success ?? currentScan?.successful_ips ?? successfulIps ?? 1;

  const filteredInfra = useMemo(() => {
    if (!hasInfra) return [];
    return infrastructure
      .filter(item => String(item.name || '').toLowerCase().includes(query.toLowerCase()))
      .sort((a, b) => {
        let cmp = 0;
        if (sortKey === 'name') cmp = String(a.name || '').localeCompare(String(b.name || ''));
        else cmp = Number(a[sortKey] || 0) - Number(b[sortKey] || 0);
        return sortDir === 'asc' ? cmp : -cmp;
      });
  }, [hasInfra, infrastructure, query, sortKey, sortDir]);

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

  // Guard against missing scans
  if (!currentScan) {
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

  const failRate = 100 - responseRate;

  return (
    <div className="app-container">
      {/* Header */}
      <header className={`app-header${isHeaderHidden ? ' is-hidden' : ''}`}>
        <div className="header-content">
          <div className="header-title">
            <span className="header-kicker">IPv6 Crawler</span>
            <h1>IPv6 Crawler Dashboard</h1>
            <p className="header-subtitle">Active IPv6 Prefix Analysis & Infrastructure Mapping</p>
          </div>
          <div className="header-meta">
            <span className="meta-pill">
              <span className="meta-label">Last Updated</span>
              <span className="meta-value">
                {dashboardData?.last_updated
                  ? new Date(dashboardData.last_updated).toLocaleString()
                  : 'Loading...'}
              </span>
            </span>
            <span className="meta-pill">
              <span className="meta-label">Phases</span>
              <span className="meta-value">
                {dashboardData?.total_scans || scans.length || 0}
              </span>
            </span>
            <span className="meta-pill">
              <span className="meta-label">Auto-refresh</span>
              <span className="meta-value">
                {lastUpdate ? `${Math.floor((Date.now() - lastUpdate.getTime()) / 1000)}s ago` : 'pending'}
              </span>
            </span>
          </div>
        </div>
      </header>

      <div className="app-body">
        {/* KPI Section */}
        <section className="kpi-section">
          <div className="kpi-grid">
            <MetricCard
              title="Total IPs"
              value={totalIps}
              subtitle="IPv6 addresses in selected scan"
              icon="🎯"
              color="#4e79a7"
            />
            <MetricCard
              title="Responsive IPs"
              value={responsiveIps}
              subtitle={`${responseRate.toFixed(2)}% responded (any protocol TRUE)`}
              icon="📡"
              color="#f28e2b"
            />
            <MetricCard
              title="Successful"
              value={successfulIps}
              subtitle={`${successRate.toFixed(2)}% status=success`}
              icon="✓"
              color="#59a14f"
            />
            <MetricCard
              title="Non-Responsive"
              value={Math.max(0, totalIps - responsiveIps)}
              subtitle={`${failRate.toFixed(2)}% no protocol responded`}
              icon="✗"
              color="#e15759"
            />
          </div>
        </section>

        {/* Status Indicators */}
        <section className="status-section">
          <h4>Performance Metrics</h4>
          <div className="status-grid">
            <StatusIndicator value={successRate} threshold={50} label="Success Rate" />
            <StatusIndicator value={responseRate} threshold={50} label="Response Rate" />
            <StatusIndicator value={Math.min(100, responseRate)} threshold={60} label="Reachability" />
          </div>
        </section>

        {/* Phase Timeline */}
        {scans.length > 0 && (
          <section className="timeline-section">
            <PhaseTimeline
              data={scans}
              selectedPhase={selectedPhase}
              onSelectPhase={setSelectedPhase}
            />
          </section>
        )}

        {/* Charts Grid */}
        <div className="charts-grid">
          {/* NEW: Port Reachability (if available) */}
          {currentScan?.port_stats && (
            <div className="chart-card full-width">
              <PortReachabilityChart portStats={currentScan.port_stats} />
            </div>
          )}

          {/* NEW: Status Distribution (if available) */}
          {currentScan?.status_distribution && (
            <div className="chart-card">
              <StatusDistributionChart statusData={currentScan.status_distribution} />
            </div>
          )}

          {/* NEW: Multi-Port Analysis (if available) */}
          {currentScan?.multi_port_analysis && currentScan.multi_port_analysis.length > 0 && (
            <div className="chart-card">
              <MultiPortAnalysisChart multiPortData={currentScan.multi_port_analysis} />
            </div>
          )}

          {/* NEW: Temporal Trends (if available) */}
          {scans.length > 1 && (
            <div className="chart-card full-width">
              <TemporalTrendsChart scanHistory={scans} />
            </div>
          )}

          {/* Legacy Infrastructure Distribution (only if present) */}
          {hasInfra && (
            <div className="chart-card">
              <InfrastructureBreakdown data={infrastructure} totalSuccess={Math.max(1, infraTotal)} />
            </div>
          )}

          {/* Top Infrastructure Providers (legacy, only if present) */}
          {hasInfra && (
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
          )}
        </div>

        {/* Infrastructure Table */}
        {hasInfra && (
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
                    <td className="percentage">{((item.count / Math.max(1, infraTotal)) * 100).toFixed(3)}%</td>
                    <td>
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{ width: `${(item.count / Math.max(1, infraTotal)) * 100}%` }}
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
        )}
      </div>

      {/* Footer */}
      <footer className="app-footer">
        <p>IPv6 Crawler Analytics | Powered by LightGBM ML Pipeline</p>
      </footer>
    </div>
  );
}

export default App;
