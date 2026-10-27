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
  /** Membro aprovado de alguma equipe (sem isso não pode informar disponibilidade). */
  em_equipe?: boolean;
  /** Vagas da equipe em que o voluntário ainda pode se oferecer. */
  vagas_abertas?: number;
  /** Avisos ainda não lidos na caixa do app (o sino do Início). */
  avisos_nao_lidos?: number;
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

/** Outra função da mesma equipe no mesmo culto; `nome` nulo = vaga sem ninguém. */
export type Colega = { funcao: string; nome: string | null; confirmada: boolean };

export type Historico = {
  mes: number;
  ano: number;
  total: number;
  desde: string | null;
  por_funcao: { funcao: string; equipe: string; total: number }[];
  ultimas: Escala[];
};

// ── Painel do líder (/lider/) ──

export type Pessoa = { id: number; nome: string };

export type EscalaDaEquipe = Pick<Escala, 'id' | 'evento' | 'funcao' | 'equipe' | 'equipe_id' | 'confirmada'>;

export type Impedimento = { id: number; motivo: string; data_solicitacao: string; pessoa: Pessoa; escala: EscalaDaEquipe };

export type Troca = { id: number; data_solicitacao: string; pessoa: Pessoa; escala: EscalaDaEquipe };

export type Candidatura = { id: number; pessoa: Pessoa; equipe: string; equipe_id: number };

/** Voluntário que se ofereceu para uma vaga em aberto. */
export type Oferta = { id: number; data_candidatura: string; pessoa: Pessoa; escala: EscalaDaEquipe };

export type PendenciasDoLider = {
  impedimentos: Impedimento[];
  trocas: Troca[];
  ofertas: Oferta[];
  candidaturas: Candidatura[];
};

/** `ofertas`: quantos se ofereceram e esperam o líder (ausente em servidor antigo). */
export type Vaga = EscalaDaEquipe & { disponiveis: number; ofertas?: number };

export type Candidato = Pessoa & { disponivel: boolean; se_ofereceu: boolean; servicos_no_mes: number };

export type DetalheDaVaga = { vaga: Vaga; candidatos: Candidato[] };

/** Vaga da equipe do voluntário (tela "Vagas em aberto"). */
export type VagaAberta = EscalaDaEquipe & { me_ofereci: boolean };

export type ContagemDoCulto = { total: number; confirmadas: number; pendentes: number; vagas: number };

/** Culto com as contagens das equipes lideradas (somadas e, em `por_equipe`, separadas). */
export type Culto = EventoComEquipe &
  ContagemDoCulto & { por_equipe: (ContagemDoCulto & { equipe_id: number; equipe: string })[] };

export type EscalaDoCulto = {
  id: number;
  funcao: string;
  equipe: string;
  pessoa: Pessoa | null;
  confirmada: boolean;
  tem_impedimento: boolean;
  troca_pendente: boolean;
  /** Só nas vagas: quem se ofereceu e quantos marcaram disponibilidade (ausentes em servidor antigo). */
  ofertas?: Pessoa[];
  disponiveis?: number | null;
};

export type DetalheDoCulto = { evento: EventoComEquipe; escalas: EscalaDoCulto[] };

export type DisponibilidadeDaEquipe = {
  equipes: Equipe[];
  equipe_id: number | null;
  ano: number | null;
  mes: number | null;
  faltantes: Pessoa[];
  membros: number;
};

/** Notificação guardada na caixa de avisos. `tipo` e `escala_id` são os mesmos do push. */
export type Aviso = {
  id: number;
  titulo: string;
  corpo: string;
  tipo: string;
  escala_id: number | null;
  /** Culto da escala (avisos de oferta abrem a tela do culto). Ausente em servidor antigo. */
  evento_id?: number | null;
  criado_em: string;
  lido: boolean;
};

export type CaixaDeAvisos = { nao_lidos: number; avisos: Aviso[] };
