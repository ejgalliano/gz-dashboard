import { useState, useEffect, useCallback } from 'react'
import { supabase } from '../lib/supabase'
import { Cliente, MetricaDiaria, ClienteComMetrica, Alerta, Periodo } from '../lib/types'
import { subDays, format } from 'date-fns'

export function useDashboard(periodo: Periodo) {
  const [clientes, setClientes] = useState<ClienteComMetrica[]>([])
  const [alertas, setAlertas] = useState<Alerta[]>([])
  const [loading, setLoading] = useState(true)
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState<string>('')

  const dias = periodo === '7d' ? 7 : periodo === '14d' ? 14 : 30

  const gerarAlertas = useCallback((data: ClienteComMetrica[]): Alerta[] => {
    const lista: Alerta[] = []
    data.forEach(c => {
      if (!c.ultimaMetrica) {
        lista.push({ tipo: 'Sem dados', mensagem: `${c.nome} sem dados recentes`, status: 'aviso', cliente: c.nome })
        return
      }
      const m = c.ultimaMetrica
      if (m.ctr > 0 && m.ctr < 0.008) {
        lista.push({ tipo: 'CTR baixo', mensagem: `${c.nome}: CTR ${(m.ctr * 100).toFixed(2)}% abaixo de 0.8%`, status: 'aviso', cliente: c.nome })
      }
      if (c.metricas.length >= 7) {
        const media7d = c.metricas.slice(-7).reduce((a, b) => a + b.cpa, 0) / 7
        if (m.cpa > 0 && media7d > 0 && m.cpa > media7d * 2) {
          lista.push({ tipo: 'CPA anômalo', mensagem: `${c.nome}: CPA R$${m.cpa.toFixed(2)} é 2x acima da média`, status: 'critico', cliente: c.nome })
        }
      }
      if (m.gasto === 0) {
        lista.push({ tipo: 'Gasto zero', mensagem: `${c.nome}: sem gasto registrado ontem`, status: 'aviso', cliente: c.nome })
      }
    })
    return lista
  }, [])

  const carregar = useCallback(async () => {
    setLoading(true)
    try {
      const dataInicio = format(subDays(new Date(), dias), 'yyyy-MM-dd')

      const { data: clientesData } = await supabase
        .from('clientes')
        .select('*')
        .eq('ativo', true)
        .order('nome')

      const { data: metricasData } = await supabase
        .from('metricas_diarias')
        .select('*')
        .gte('data', dataInicio)
        .order('data', { ascending: true })

      if (!clientesData) return

      const clientesComMetrica: ClienteComMetrica[] = (clientesData as Cliente[]).map(c => {
        const metricas = (metricasData as MetricaDiaria[] || []).filter(m => m.cliente_id === c.id)
        const gasto7d = metricas.slice(-7).reduce((a, b) => a + (b.gasto || 0), 0)
        const cliques7d = metricas.slice(-7).reduce((a, b) => a + (b.cliques || 0), 0)
        const conversoes7d = metricas.slice(-7).reduce((a, b) => a + (b.conversoes || 0), 0)
        const spend7d = metricas.slice(-7).reduce((a, b) => a + (b.gasto || 0), 0)
        const receita7d = metricas.slice(-7).reduce((a, b) => a + (b.receita || 0), 0)
        const roas7d = spend7d > 0 ? receita7d / spend7d : 0
        return {
          ...c,
          metricas,
          ultimaMetrica: metricas[metricas.length - 1],
          gasto7d,
          cliques7d,
          conversoes7d,
          roas7d,
        }
      })

      setClientes(clientesComMetrica)
      setAlertas(gerarAlertas(clientesComMetrica))

      if (metricasData && metricasData.length > 0) {
        const ultima = metricasData[metricasData.length - 1] as MetricaDiaria
        setUltimaAtualizacao(ultima.coletado_em)
      }
    } finally {
      setLoading(false)
    }
  }, [dias, gerarAlertas])

  useEffect(() => { carregar() }, [carregar])

  const totais = {
    gasto: clientes.reduce((a, c) => a + c.gasto7d, 0),
    cliques: clientes.reduce((a, c) => a + c.cliques7d, 0),
    conversoes: clientes.reduce((a, c) => a + c.conversoes7d, 0),
    clientesAtivos: clientes.filter(c => c.ultimaMetrica && c.ultimaMetrica.gasto > 0).length,
  }

  return { clientes, alertas, loading, ultimaAtualizacao, totais, recarregar: carregar }
}
