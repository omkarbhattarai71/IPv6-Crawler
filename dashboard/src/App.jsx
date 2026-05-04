import React, { useEffect, useMemo, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LabelList,
  Cell
} from 'recharts';
import 'bootstrap/dist/css/bootstrap.min.css';

// Import the aggregated JSON data directly
import dashboardData from './dashboard_data.json';

const COLORS = ['#4e79a7', '#59a14f', '#9c755f', '#f28e2b', '#e15759', '#76b7b2'];

const truncate = (text, max = 40) => (text.length > max ? `${text.slice(0, max)}…` : text);

function App() {
  const { scan_stats, top_infrastructure } = dashboardData;

  const [query, setQuery] = useState('');
  const [showAll, setShowAll] = useState(false);
  const [topN, setTopN] = useState(10);
  const [selectedHost, setSelectedHost] = useState(null);

  // Table controls
  const [sortKey, setSortKey] = useState('count'); // name | count | share | rank
  const [sortDir, setSortDir] = useState('desc');  // asc | desc
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const totalActive = scan_stats.success || 1;

  const sortedData = useMemo(
    () => [...top_infrastructure].sort((a, b) => b.count - a.count),
    [top_infrastructure]
  );

  const rankByName = useMemo(() => {
    const map = new Map();
    sortedData.forEach((d, i) => map.set(d.name, i + 1));
    return map;
  }, [sortedData]);

  const filteredData = useMemo(
    () => sortedData.filter((d) => d.name.toLowerCase().includes(query.toLowerCase().trim())),
    [sortedData, query]
  );

  const visibleData = useMemo(
    () => (showAll ? filteredData : filteredData.slice(0, topN)),
    [filteredData, showAll, topN]
  );

  const chartData = useMemo(
    () =>
      visibleData.map((d) => ({
        ...d,
        share: Number(((d.count / totalActive) * 100).toFixed(3))
      })),
    [visibleData, totalActive]
  );

  const chartHeight = Math.max(420, chartData.length * 44);

  const coveredByVisible = chartData.reduce((acc, d) => acc + d.count, 0);
  const coveredPct = ((coveredByVisible / totalActive) * 100).toFixed(2);

  const tableRows = useMemo(
    () =>
      filteredData.map((d) => ({
        ...d,
        rank: rankByName.get(d.name) ?? null,
        share: Number(((d.count / totalActive) * 100).toFixed(3))
      })),
    [filteredData, rankByName, totalActive]
  );

  const sortedTableRows = useMemo(() => {
    const rows = [...tableRows];
    rows.sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'name') cmp = a.name.localeCompare(b.name);
      else cmp = Number(a[sortKey]) - Number(b[sortKey]);
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return rows;
  }, [tableRows, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sortedTableRows.length / pageSize));
  const pagedRows = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedTableRows.slice(start, start + pageSize);
  }, [sortedTableRows, page, pageSize]);

  useEffect(() => {
    setPage(1);
  }, [query, pageSize, sortKey, sortDir]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const toggleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir(key === 'name' ? 'asc' : 'desc');
    }
  };

  const sortIndicator = (key) => (sortKey === key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '');

  return (
    <div className="container mt-5">
      <h1 className="mb-2 text-primary">IPv6 Discovery Dashboard</h1>
      <p className="lead mb-4">Predictive Web Server Fingerprinting & CDN Analysis</p>

      {/* High-Level Stats Cards */}
      <div className="row mb-4">
        <div className="col-md-3">
          <div className="card text-white bg-dark mb-3">
            <div className="card-body">
              <h5 className="card-title">Total Probed</h5>
              <h2 className="card-text">{scan_stats.total.toLocaleString()}</h2>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card text-white bg-success mb-3">
            <div className="card-body">
              <h5 className="card-title">Active Servers</h5>
              <h2 className="card-text">{scan_stats.success.toLocaleString()}</h2>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card text-white bg-danger mb-3">
            <div className="card-body">
              <h5 className="card-title">Reset</h5>
              <h2 className="card-text">{scan_stats.failed.toLocaleString()}</h2>
            </div>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card text-white bg-info mb-3">
            <div className="card-body">
              <h5 className="card-title">Hit Rate</h5>
              <h2 className="card-text">{Number(scan_stats.hit_rate_percentage).toFixed(2)}%</h2>
            </div>
          </div>
        </div>
      </div>

      {/* Controls + Extra Info */}
      <div className="card shadow-sm mb-3">
        <div className="card-body">
          <div className="row g-3 align-items-end">
            <div className="col-md-5">
              <label className="form-label mb-1">Search host / certificate / server name</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. localhost, technicolor, nflxvideo"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>

            <div className="col-md-3">
              <label className="form-label mb-1">Top N</label>
              <select
                className="form-select"
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
                disabled={showAll}
              >
                {[5, 10, 15, 20, 30, 50].map((n) => (
                  <option key={n} value={n}>
                    Top {n}
                  </option>
                ))}
              </select>
            </div>

            <div className="col-md-2">
              <button
                className={`btn w-100 ${showAll ? 'btn-primary' : 'btn-outline-primary'}`}
                onClick={() => setShowAll((s) => !s)}
              >
                {showAll ? 'Showing All' : 'Show All'}
              </button>
            </div>

            <div className="col-md-2">
              <button
                className="btn btn-outline-secondary w-100"
                onClick={() => {
                  setQuery('');
                  setTopN(10);
                  setShowAll(false);
                  setSelectedHost(null);
                  setSortKey('count');
                  setSortDir('desc');
                  setPage(1);
                  setPageSize(10);
                }}
              >
                Reset Filters
              </button>
            </div>
          </div>

          <div className="mt-3 small text-muted">
            Visible hosts: <strong>{chartData.length}</strong> / {top_infrastructure.length} • Coverage of active servers:{' '}
            <strong>{coveredByVisible.toLocaleString()}</strong> ({coveredPct}%)
          </div>
        </div>
      </div>

      {/* Infrastructure Fingerprinting Chart */}
      <div className="card shadow-sm">
        <div className="card-header bg-white border-0 pt-4 pb-0">
          <h4 className="mb-1">Top Discovered Infrastructure (CDN / Server Names)</h4>
          <p className="text-muted mb-0 small">Click a bar to inspect details</p>
        </div>
        <div className="card-body">
          <div style={{ height: `${chartHeight}px`, width: '100%' }}>
            <ResponsiveContainer>
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 20, right: 40, left: 200, bottom: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={220}
                  tickFormatter={(value) => truncate(value, 34)}
                />
                <Tooltip
                  formatter={(value, name, payload) => {
                    if (name === 'count') {
                      return [`${Number(value).toLocaleString()} (${payload.payload.share}%)`, 'Active Instances'];
                    }
                    return [value, name];
                  }}
                  labelFormatter={(label) => `Host: ${label}`}
                />
                <Legend />
                <Bar
                  dataKey="count"
                  name="Active Instances"
                  onClick={(payload) => setSelectedHost(payload)}
                  cursor="pointer"
                >
                  {chartData.map((_, idx) => (
                    <Cell key={`cell-${idx}`} fill={COLORS[idx % COLORS.length]} />
                  ))}
                  <LabelList dataKey="count" position="right" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {selectedHost && (
        <div className="alert alert-light border mt-3">
          <h6 className="mb-1">Selected Host</h6>
          <div><strong>Name:</strong> {selectedHost.name}</div>
          <div><strong>Active Instances:</strong> {selectedHost.count.toLocaleString()}</div>
          <div><strong>Share of Active Servers:</strong> {((selectedHost.count / totalActive) * 100).toFixed(3)}%</div>
        </div>
      )}

      {/* Full host table */}
      <div className="card shadow-sm mt-3 mb-5">
        <div className="card-header bg-white border-0 pt-4 pb-0">
          <h4 className="mb-1">All Matching Hosts</h4>
          <p className="text-muted mb-0 small">Sortable + paginated (click row to select)</p>
        </div>
        <div className="card-body">
          <div className="table-responsive">
            <table className="table table-hover align-middle">
              <thead>
                <tr>
                  <th role="button" onClick={() => toggleSort('rank')}>Rank{sortIndicator('rank')}</th>
                  <th role="button" onClick={() => toggleSort('name')}>Name{sortIndicator('name')}</th>
                  <th role="button" onClick={() => toggleSort('count')}>Count{sortIndicator('count')}</th>
                  <th role="button" onClick={() => toggleSort('share')}>Share % of Active{sortIndicator('share')}</th>
                </tr>
              </thead>
              <tbody>
                {pagedRows.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center text-muted py-4">
                      No hosts match the current filter.
                    </td>
                  </tr>
                ) : (
                  pagedRows.map((row) => (
                    <tr
                      key={row.name}
                      role="button"
                      className={selectedHost?.name === row.name ? 'table-primary' : ''}
                      onClick={() => setSelectedHost(row)}
                    >
                      <td>{row.rank}</td>
                      <td title={row.name}>{row.name}</td>
                      <td>{row.count.toLocaleString()}</td>
                      <td>{row.share.toFixed(3)}%</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mt-2">
            <div className="small text-muted">
              Showing {(pagedRows.length ? (page - 1) * pageSize + 1 : 0)}–
              {Math.min(page * pageSize, sortedTableRows.length)} of {sortedTableRows.length}
            </div>

            <div className="d-flex align-items-center gap-2">
              <label className="small text-muted mb-0">Rows</label>
              <select
                className="form-select form-select-sm"
                style={{ width: 90 }}
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value))}
              >
                {[5, 10, 20, 50].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>

              <button
                className="btn btn-sm btn-outline-secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Prev
              </button>
              <span className="small">Page {page} / {totalPages}</span>
              <button
                className="btn btn-sm btn-outline-secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

// import React from 'react';
// import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
// import 'bootstrap/dist/css/bootstrap.min.css';

// // Import the aggregated JSON data directly
// import dashboardData from './dashboard_data.json';

// function App() {
//   const { scan_stats, top_infrastructure } = dashboardData;

//   return (
//     <div className="container mt-5">
//       <h1 className="mb-4 text-primary">IPv6 Discovery Dashboard</h1>
//       <p className="lead">Predictive Web Server Fingerprinting & CDN Analysis</p>

//       {/* High-Level Stats Cards */}
//       <div className="row mb-5">
//         <div className="col-md-3">
//           <div className="card text-white bg-dark mb-3">
//             <div className="card-body">
//               <h5 className="card-title">Total Probed</h5>
//               <h2 className="card-text">{scan_stats.total.toLocaleString()}</h2>
//             </div>
//           </div>
//         </div>
//         <div className="col-md-3">
//           <div className="card text-white bg-success mb-3">
//             <div className="card-body">
//               <h5 className="card-title">Active Servers</h5>
//               <h2 className="card-text">{scan_stats.success.toLocaleString()}</h2>
//             </div>
//           </div>
//         </div>
//         <div className="col-md-3">
//           <div className="card text-white bg-danger mb-3">
//             <div className="card-body">
//               <h5 className="card-title">Reset</h5>
//               <h2 className="card-text">{scan_stats.failed.toLocaleString()}</h2>
//             </div>
//           </div>
//         </div>
//         <div className="col-md-3">
//           <div className="card text-white bg-info mb-3">
//             <div className="card-body">
//               <h5 className="card-title">Hit Rate</h5>
//               <h2 className="card-text">{scan_stats.hit_rate_percentage}%</h2>
//             </div>
//           </div>
//         </div>
//       </div>

//       {/* Infrastructure Fingerprinting Chart */}
//       <div className="card shadow-sm">
//         <div className="card-header bg-white border-0 pt-4 pb-0">
//           <h4>Top Discovered Infrastructure (CDN / Server Names)</h4>
//         </div>
//         <div className="card-body">
//           <div style={{ height: '400px', width: '100%' }}>
//             <ResponsiveContainer>
//               <BarChart
//                 data={top_infrastructure}
//                 layout="vertical"
//                 margin={{ top: 20, right: 30, left: 100, bottom: 5 }}
//               >
//                 <CartesianGrid strokeDasharray="3 3" />
//                 <XAxis type="number" />
//                 <YAxis dataKey="name" type="category" width={150} />
//                 <Tooltip />
//                 <Legend />
//                 <Bar dataKey="count" fill="#8884d8" name="Active Instances" />
//               </BarChart>
//             </ResponsiveContainer>
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// }

// export default App;