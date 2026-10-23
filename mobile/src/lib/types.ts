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

/** Evento com a equipe dona dele (null = culto geral, aberto a todos). */
export type EventoComEquipe = Evento & {
  equipe_id: number | null;
  equipe: string | null;
};

export type EventoCalendario = EventoComEquipe & {
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
  /** Impedimentos, trocas e candidaturas esperando o líder (0 para quem não lidera). */
  pendencias_lider?: number;
};

export type Disponibilidade = {
  id: number;
  data_inicio: string;
  data_fim: string;
  evento_id: number | null;
  evento: string | null;
};

export type Equipe = { id: number; nome: string };

export type Equipes = { aprovadas: Equipe[]; pendentes: Equipe[]; disponiveis: Equipe[] };

/** Links do .ics das escalas (sem login; trocar a senha invalida). */
export type Agenda = { https: string; webcal: string };

// ── Painel do líder (/lider/) ──

export type Pessoa = { id: number; nome: string };

export type EscalaDaEquipe = Pick<Escala, 'id' | 'evento' | 'funcao' | 'equipe' | 'equipe_id' | 'confirmada'>;

export type Impedimento = { id: number; motivo: string; data_solicitacao: string; pessoa: Pessoa; escala: EscalaDaEquipe };

export type Troca = { id: number; data_solicitacao: string; pessoa: Pessoa; escala: EscalaDaEquipe };

export type Candidatura = { id: number; pessoa: Pessoa; equipe: string; equipe_id: number };

export type PendenciasDoLider = { impedimentos: Impedimento[]; trocas: Troca[]; candidaturas: Candidatura[] };

export type Vaga = EscalaDaEquipe & { disponiveis: number };

export type Candidato = Pessoa & { disponivel: boolean; servicos_no_mes: number };

export type DetalheDaVaga = { vaga: Vaga; candidatos: Candidato[] };
