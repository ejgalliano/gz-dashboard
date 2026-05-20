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
  cliques: number
  conversoes: number
  receita: number
  cpa: number
  ctr: number
  roas: number
  coletado_em: string
}

export interface ClienteComMetrica extends Cliente {
  metricas: MetricaDiaria[]
  ultimaMetrica?: MetricaDiaria
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
