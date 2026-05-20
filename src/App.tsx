import React, { useState } from 'react'
import { useDashboard } from './hooks/useDashboard'
import { Periodo, ClienteComMetrica, Alerta } from './lib/types'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import './App.css'

function KpiCard({ label, value, sub, cor }: { label: string; value: string; sub?: string; cor?: string }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value" style={{ color: cor }}>{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  )
}

function DiasRestantesBadge({ dias }: { dias: number | null }) {
  if (dias === null) return <span className="badge badge-warn">—</span>
  if (dias <= 3) return <span className="badge badge-crit">{dias}d ⚠️</span>
  if (dias <= 7) return <span className="badge badge-warn">{dias}d</span>
  return <span className="badge badge-ok">{dias}d</span>
}

function StatusBadge({ cliente }: { cliente: ClienteComMetrica }) {
  if (!cliente.ultimaMetrica) return <span className="badge badge-warn">sem dados</span>
  if (cliente.ultimaMetrica.gasto === 0) return <span className="badge badge-warn">pausado</span>
  return <span className="badge badge-ok">ativo</span>
}

function AlertaBadge({ status }: { status: string }) {
  const map: Record<string, string> = { ok: 'badge-ok', aviso: 'badge-warn', critico: 'badge-crit' }
  const label: Record<string, string> = { ok: 'OK', aviso: 'Atenção', critico: 'Crítico' }
  return <span className={`badge ${map[status] || 'badge-warn'}`}>{label[status] || status}</span>
}

function GraficoEvolucao({ clientes, periodo }: { clientes: ClienteComMetrica[]; periodo: Periodo }) {
  const dias = periodo === '7d' ? 7 : periodo === '14d' ? 14 : 30
  const datesMap: Record<string, { data: string; gasto: number }> = {}
  clientes.forEach(c => {
    c.metricas.slice(-dias).forEach(m => {
      if (!datesMap[m.data]) datesMap[m.data] = { data: m.data, gasto: 0 }
      datesMap[m.data].gasto += m.gasto || 0
    })
  })
  const dados = Object.values(datesMap).sort((a, b) => a.data.localeCompare(b.data)).map(d => ({
    ...d,
    dataFmt: format(parseISO(d.data), 'dd/MM', { locale: ptBR }),
    gasto: parseFloat(d.gasto.toFixed(2)),
  }))
  if (dados.length === 0) return <div className="empty-state">Sem dados para o período</div>
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={dados} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="dataFmt" tick={{ fontSize: 11, fill: '#888' }} />
        <YAxis tick={{ fontSize: 11, fill: '#888' }} tickFormatter={v => `R$${v}`} />
        <Tooltip formatter={(v: any) => [`R$${Number(v).toFixed(2)}`, 'Gasto']} />
        <Line type="monotone" dataKey="gasto" stroke="#1a56a0" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}

function GraficoBarras({ clientes }: { clientes: ClienteComMetrica[] }) {
  const dados = clientes
    .filter(c => c.gasto7d > 0)
    .sort((a, b) => b.gasto7d - a.gasto7d)
    .map(c => ({ nome: c.nome.length > 12 ? c.nome.slice(0, 12) + '…' : c.nome, gasto: parseFloat(c.gasto7d.toFixed(2)) }))
  if (dados.length === 0) return <div className="empty-state">Sem dados</div>
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={dados} margin={{ top: 5, right: 20, left: 0, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="nome" tick={{ fontSize: 10, fill: '#888' }} angle={-20} textAnchor="end" />
        <YAxis tick={{ fontSize: 11, fill: '#888' }} tickFormatter={v => `R$${v}`} />
        <Tooltip formatter={(v: any) => [`R$${Number(v).toFixed(2)}`, 'Gasto 7d']} />
        <Bar dataKey="gasto" fill="#1a56a0" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export default function App() {
  const [periodo, setPeriodo] = useState<Periodo>('7d')
  const [tabela, setTabela] = useState<'clientes' | 'alertas'>('clientes')
  const { clientes, alertas, loading, ultimaAtualizacao, totais, recarregar } = useDashboard(periodo)

  const fmtData = (d: string) => {
    try { return format(parseISO(d), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR }) } catch { return d }
  }

  const fmt = (v: number, prefix = 'R$', decimals = 2) =>
    v > 0 ? `${prefix}${v.toFixed(decimals)}` : '—'

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <div className="logo">GZ</div>
          <div>
            <div className="header-title">GZ Marketing Dashboard</div>
            <div className="header-sub">Meta Ads · {clientes.length} clientes</div>
          </div>
        </div>
        <div className="header-right">
          {ultimaAtualizacao && <span className="ultima-atualizacao">Atualizado {fmtData(ultimaAtualizacao)}</span>}
          <div className="periodo-tabs">
            {(['7d', '14d', '30d'] as Periodo[]).map(p => (
              <button key={p} className={`periodo-btn ${periodo === p ? 'ativo' : ''}`} onClick={() => setPeriodo(p)}>
                {p === '7d' ? '7 dias' : p === '14d' ? '14 dias' : '30 dias'}
              </button>
            ))}
          </div>
          <button className="btn-refresh" onClick={recarregar} title="Recarregar">↻</button>
        </div>
      </header>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Carregando dados...</span></div>
      ) : (
        <main className="main">
          <div className="kpi-grid">
            <KpiCard label="Gasto total" value={`R$${totais.gasto.toFixed(2)}`} sub={`últimos ${periodo}`} />
            <KpiCard label="Saldo total" value={`R$${totais.saldoTotal.toFixed(2)}`} sub="todas as contas" cor={totais.saldoTotal < 100 ? '#c0392b' : '#1a7a3c'} />
            <KpiCard label="Total de cliques" value={totais.cliques.toLocaleString('pt-BR')} sub={`últimos ${periodo}`} />
            <KpiCard label="Conversões" value={totais.conversoes.toString()} sub={`últimos ${periodo}`} />
            <KpiCard label="Clientes ativos" value={`${totais.clientesAtivos}/${clientes.length}`} sub="com gasto ontem" cor={totais.clientesAtivos < clientes.length ? '#c0392b' : '#1a7a3c'} />
            <KpiCard label="Alertas" value={alertas.length.toString()} sub={`${alertas.filter((a: Alerta) => a.status === 'critico').length} críticos`} cor={alertas.some((a: Alerta) => a.status === 'critico') ? '#c0392b' : '#888'} />
          </div>

          <div className="graficos-grid">
            <div className="card">
              <div className="card-title">Evolução de gasto diário</div>
              <GraficoEvolucao clientes={clientes} periodo={periodo} />
            </div>
            <div className="card">
              <div className="card-title">Gasto por cliente (7 dias)</div>
              <GraficoBarras clientes={clientes} />
            </div>
          </div>

          <div className="card">
            <div className="tab-bar">
              <button className={`tab-btn ${tabela === 'clientes' ? 'ativo' : ''}`} onClick={() => setTabela('clientes')}>
                Clientes ({clientes.length})
              </button>
              <button className={`tab-btn ${tabela === 'alertas' ? 'ativo' : ''}`} onClick={() => setTabela('alertas')}>
                Alertas {alertas.length > 0 && <span className="badge-count">{alertas.length}</span>}
              </button>
            </div>

            {tabela === 'clientes' && (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Cliente</th>
                      <th>Saldo</th>
                      <th>Orç. diário</th>
                      <th>Campanhas ativas</th>
                      <th>Dias restantes</th>
                      <th>Gasto {periodo}</th>
                      <th>Alcance</th>
                      <th>CTR</th>
                      <th>CPC</th>
                      <th>CPA</th>
                      <th>CPL</th>
                      <th>ROAS</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {clientes.map(c => (
                      <tr key={c.id}>
                        <td><strong>{c.nome}</strong></td>
                        <td>{c.balance ? `R$${c.balance.balance.toFixed(2)}` : '—'}</td>
                        <td>{c.balance ? `R$${c.balance.orcamento_diario_ativo.toFixed(2)}` : '—'}</td>
                        <td>{c.balance?.campanhas_ativas ?? '—'}</td>
                        <td><DiasRestantesBadge dias={c.balance?.dias_restantes ?? null} /></td>
                        <td>R${c.gasto7d.toFixed(2)}</td>
                        <td>{c.ultimaMetrica?.alcance ? c.ultimaMetrica.alcance.toLocaleString('pt-BR') : '—'}</td>
                        <td>{c.ultimaMetrica?.ctr ? (c.ultimaMetrica.ctr * 100).toFixed(2) + '%' : '—'}</td>
                        <td>{fmt(c.ultimaMetrica?.cpc || 0)}</td>
                        <td>{fmt(c.ultimaMetrica?.cpa || 0)}</td>
                        <td>{fmt(c.ultimaMetrica?.cpl || 0)}</td>
                        <td>{c.roas7d > 0 ? c.roas7d.toFixed(2) + 'x' : '—'}</td>
                        <td><StatusBadge cliente={c} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {tabela === 'alertas' && (
              alertas.length === 0
                ? <div className="empty-state">Nenhum alerta no momento ✓</div>
                : (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead><tr><th>Cliente</th><th>Tipo</th><th>Mensagem</th><th>Status</th></tr></thead>
                      <tbody>
                        {alertas.map((a: Alerta, i: number) => (
                          <tr key={i}>
                            <td><strong>{a.cliente}</strong></td>
                            <td>{a.tipo}</td>
                            <td>{a.mensagem}</td>
                            <td><AlertaBadge status={a.status} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )
            )}
          </div>
        </main>
      )}
    </div>
  )
}