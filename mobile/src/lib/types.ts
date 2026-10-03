// Formatos devolvidos pela API (/api/v1/). Ver api/serializers/ no backend.

export type Usuario = {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  nome_completo: string;
  email: string;
  telefone: string | null;
  aniversario: string | null;
  precisa_definir_senha: boolean;
  precisa_aceitar_termo: boolean;
  em_equipe: boolean;
  lider: boolean;
};

export type Evento = {
  id: number;
  nome: string;
  data_inicio: string;
  data_fim: string;
  observacao: string | null;
};

export type EventoCalendario = Evento & {
  equipe_id: number | null;
  equipe: string | null;
  escalado: boolean;
  confirmada: boolean;
  funcoes: string[];
};

export type Escala = {
  id: number;
  evento: Evento;
  funcao: string;
  equipe: string;
  equipe_id: number;
  confirmada: boolean;
  data_confirmacao: string | null;
  tem_impedimento: boolean;
  troca_pendente: boolean;
};

export type Home = {
  tem_disponibilidade: boolean;
  tem_escalas: boolean;
  escalas_pendentes: number;
  falta_email: boolean;
  falta_telefone: boolean;
  proxima_escala: Escala | null;
};

export type Periodo = {
  id: number;
  data_inicio: string;
  data_fim: string;
  evento_id: number | null;
  evento: string | null;
};

export type Equipe = { id: number; nome: string };

export type Equipes = { aprovadas: Equipe[]; pendentes: Equipe[]; disponiveis: Equipe[] };

/** Os dois tipos de período têm as mesmas rotas na API. */
export type TipoPeriodo = 'disponibilidades' | 'indisponibilidades';
