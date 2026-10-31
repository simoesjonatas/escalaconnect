import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './api';
import {
  Agenda,
  CaixaDeAvisos,
  Colega,
  Culto,
  DetalheDaVaga,
  DetalheDoCulto,
  DisponibilidadeDaEquipe,
  Disponibilidade,
  Equipes,
  Escala,
  EventoCalendario,
  EventoComEquipe,
  Historico,
  Home,
  PendenciasDoLider,
  Vaga,
  VagaAberta,
} from './types';

export const useHome = () => useQuery({ queryKey: ['home'], queryFn: () => api<Home>('GET', '/home/') });

export const useEscalas = () => useQuery({ queryKey: ['escalas'], queryFn: () => api<Escala[]>('GET', '/escalas/') });

export const useEscala = (id: number) =>
  useQuery({ queryKey: ['escalas', id], queryFn: () => api<Escala>('GET', `/escalas/${id}/`) });

export type AcaoDeEscala =
  | { tipo: 'confirmar' }
  | { tipo: 'impedimento'; motivo: string }
  | { tipo: 'pedir-troca' }
  | { tipo: 'cancelar-impedimento' }
  | { tipo: 'cancelar-troca' };

/** Confirmar, sinalizar ou cancelar impedimento, pedir ou cancelar troca: todas devolvem a escala atualizada. */
export function useAcaoDeEscala(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (acao: AcaoDeEscala) => {
      switch (acao.tipo) {
        case 'confirmar':
          return api<Escala>('POST', `/escalas/${id}/confirmar/`);
        case 'impedimento':
          return api<Escala>('POST', `/escalas/${id}/impedimento/`, { motivo: acao.motivo });
        case 'cancelar-impedimento':
          return api<Escala>('DELETE', `/escalas/${id}/impedimento/`);
        case 'pedir-troca':
          return api<Escala>('POST', `/escalas/${id}/troca/`);
        case 'cancelar-troca':
          return api<Escala>('DELETE', `/escalas/${id}/troca/`);
      }
    },
    onSuccess: (escala) => {
      queryClient.setQueryData(['escalas', id], escala);
      // Lista, início e calendário mostram o estado da escala.
      for (const chave of ['escalas', 'home', 'eventos']) void queryClient.invalidateQueries({ queryKey: [chave] });
    },
  });
}

export const useEventos = (inicio: string, fim: string) =>
  useQuery({
    queryKey: ['eventos', inicio, fim],
    queryFn: () => api<EventoCalendario[]>('GET', `/eventos/?inicio=${inicio}&fim=${fim}`),
  });

export const useDisponibilidades = () =>
  useQuery({ queryKey: ['disponibilidades'], queryFn: () => api<Disponibilidade[]>('GET', '/disponibilidades/') });

/** Eventos dos próximos 60 dias em que o voluntário ainda não marcou disponibilidade. */
export const useEventosElegiveis = () =>
  useQuery({
    queryKey: ['disponibilidades', 'eventos'],
    queryFn: () => api<EventoComEquipe[]>('GET', '/disponibilidades/eventos/'),
  });

export type MudancaDeDisponibilidade = { acao: 'por-evento'; evento_ids: number[] } | { acao: 'excluir'; id: number };

export function useMudarDisponibilidades() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mudanca: MudancaDeDisponibilidade) =>
      mudanca.acao === 'por-evento'
        ? api('POST', '/disponibilidades/por-evento/', { evento_ids: mudanca.evento_ids })
        : api('DELETE', `/disponibilidades/${mudanca.id}/`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['disponibilidades'] });
      void queryClient.invalidateQueries({ queryKey: ['home'] });
    },
  });
}

export const useEquipes = () => useQuery({ queryKey: ['equipes'], queryFn: () => api<Equipes>('GET', '/equipes/') });

export function useCandidatura() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ equipeId, cancelar }: { equipeId: number; cancelar?: boolean }) =>
      api<Equipes>(cancelar ? 'DELETE' : 'POST', `/equipes/${equipeId}/candidatura/`),
    onSuccess: (equipes) => {
      queryClient.setQueryData(['equipes'], equipes);
      void queryClient.invalidateQueries({ queryKey: ['home'] });
    },
  });
}

export const useAgenda = () =>
  useQuery({ queryKey: ['agenda'], queryFn: () => api<Agenda>('GET', '/me/agenda/'), staleTime: Infinity });

export const useColegas = (id: number) =>
  useQuery({ queryKey: ['escalas', id, 'equipe'], queryFn: () => api<Colega[]>('GET', `/escalas/${id}/equipe/`) });

export const useHistorico = () =>
  useQuery({ queryKey: ['historico'], queryFn: () => api<Historico>('GET', '/me/historico/') });

// ── Painel do líder ──

export const usePendenciasDoLider = () =>
  useQuery({ queryKey: ['lider', 'pendencias'], queryFn: () => api<PendenciasDoLider>('GET', '/lider/pendencias/') });

/** `ativo` false: não busca (ex.: o Calendário de quem não é líder). */
export const useVagas = (ativo = true) =>
  useQuery({ queryKey: ['lider', 'vagas'], queryFn: () => api<Vaga[]>('GET', '/lider/vagas/'), enabled: ativo });

export const useVaga = (id: number) =>
  useQuery({ queryKey: ['lider', 'vagas', id], queryFn: () => api<DetalheDaVaga>('GET', `/lider/vagas/${id}/`) });

export type AcaoDoLider = {
  tipo: 'impedimentos' | 'trocas' | 'ofertas' | 'candidaturas';
  id: number;
  acao: 'aprovar' | 'recusar';
};

function useAtualizarPainel() {
  const queryClient = useQueryClient();
  // Painel, contador da aba e as telas do voluntário que mostram as mesmas escalas.
  return () => {
    for (const chave of ['lider', 'home', 'escalas', 'eventos', 'vagas']) {
      void queryClient.invalidateQueries({ queryKey: [chave] });
    }
  };
}

/** Aprovar/recusar uma pendência. Aprovar impedimento ou troca devolve a vaga liberada. */
export function useAcaoDoLider() {
  const atualizar = useAtualizarPainel();
  return useMutation({
    mutationFn: ({ tipo, id, acao }: AcaoDoLider) =>
      api<{ vaga_id: number } | undefined>('POST', `/lider/${tipo}/${id}/${acao}/`),
    onSuccess: atualizar,
  });
}

export function useEscalarNaVaga(vagaId: number) {
  const atualizar = useAtualizarPainel();
  return useMutation({
    mutationFn: (usuarioId: number) => api('POST', `/lider/vagas/${vagaId}/escalar/`, { usuario_id: usuarioId }),
    onSuccess: atualizar,
  });
}

export const useCultos = (ativo = true) =>
  useQuery({ queryKey: ['lider', 'cultos'], queryFn: () => api<Culto[]>('GET', '/lider/cultos/'), enabled: ativo });

export const useCulto = (id: number) =>
  useQuery({ queryKey: ['lider', 'cultos', id], queryFn: () => api<DetalheDoCulto>('GET', `/lider/cultos/${id}/`) });

export type CanalDoPedido = 'app' | 'todos';

/** Pede a confirmação (só app, ou e-mail e app) de quem ainda não confirmou no culto; devolve quantos eram. */
export function usePedirConfirmacao(eventoId: number) {
  return useMutation({
    mutationFn: (canal: CanalDoPedido) =>
      api<{ pendentes: number }>('POST', `/lider/cultos/${eventoId}/pedir-confirmacao/`, { canal }),
  });
}

export type FiltroDeDisponibilidade = { equipe?: number; ano?: number; mes?: number };

export const useDisponibilidadeDaEquipe = ({ equipe, ano, mes }: FiltroDeDisponibilidade) =>
  useQuery({
    queryKey: ['lider', 'disponibilidade', equipe, ano, mes],
    queryFn: () => {
      const params = Object.entries({ equipe, ano, mes })
        .filter(([, valor]) => valor !== undefined)
        .map(([chave, valor]) => `${chave}=${valor}`)
        .join('&');
      return api<DisponibilidadeDaEquipe>('GET', `/lider/disponibilidade/${params ? `?${params}` : ''}`);
    },
  });

export type PedidoDeDisponibilidade = { equipe_id: number; ano: number; mes: number; canal: CanalDoPedido };

export const usePedirDisponibilidade = () =>
  useMutation({
    mutationFn: (pedido: PedidoDeDisponibilidade) =>
      api<{ faltantes: number }>('POST', '/lider/disponibilidade/pedir/', pedido),
  });

// ── Vagas em aberto (voluntário) ──

export const useVagasAbertas = () =>
  useQuery({ queryKey: ['vagas'], queryFn: () => api<VagaAberta[]>('GET', '/vagas/') });

/** Oferecer-se para uma vaga (ou desistir da oferta). */
export function useOferta() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ vagaId, desistir }: { vagaId: number; desistir?: boolean }) =>
      api<VagaAberta | null>(desistir ? 'DELETE' : 'POST', `/vagas/${vagaId}/oferta/`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['vagas'] });
      void queryClient.invalidateQueries({ queryKey: ['home'] });
      // Quem também lidera a equipe vê a oferta no painel e na prévia do Calendário.
      void queryClient.invalidateQueries({ queryKey: ['lider'] });
    },
  });
}

// ── Caixa de avisos ──

export const useAvisos = () =>
  useQuery({ queryKey: ['avisos'], queryFn: () => api<CaixaDeAvisos>('GET', '/avisos/') });

/** Marca todos os avisos como lidos; atualiza o sino (contador da /home/). */
export function useMarcarAvisosLidos() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api<{ nao_lidos: number }>('POST', '/avisos/ler/'),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['home'] }),
  });
}
