export interface Cliente {
  id: number
  nome: string
  plataforma: string
  account_id: string
  ativo: boolean
  criado_em: string
}

export interface MetricaDiaria {
  id: number
  cliente_id: number
  data: string
  gasto: number
  impressoes: number
  alcance: number
  frequencia: number
  cliques: number
  conversoes: number
  receita: number
  leads: number
  cpa: number
  cpl: number
  cpc: number
  cpm: number
  ctr: number
  roas: number
  coletado_em: string
}

export interface AccountBalance {
  id: number
  cliente_id: number
  account_id: string
  balance: number
  amount_spent: number
  currency: string
  orcamento_diario_ativo: number
  gasto_7d: number
  media_diaria_7d: number
  dias_restantes: number | null
  coletado_em: string
}

export interface ClienteComMetrica extends Cliente {
  metricas: MetricaDiaria[]
  ultimaMetrica?: MetricaDiaria
  balance?: AccountBalance
  gasto7d: number
  cliques7d: number
  conversoes7d: number
  roas7d: number
}

export type Periodo = '7d' | '14d' | '30d'
export type StatusAlerta = 'ok' | 'aviso' | 'critico'

export interface Alerta {
  tipo: string
  mensagem: string
  status: StatusAlerta
  cliente: string
}