import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './api';
import { Disponibilidade, Equipes, Escala, Evento, EventoCalendario, Home } from './types';

export const useHome = () => useQuery({ queryKey: ['home'], queryFn: () => api<Home>('GET', '/home/') });

export const useEscalas = () => useQuery({ queryKey: ['escalas'], queryFn: () => api<Escala[]>('GET', '/escalas/') });

export const useEscala = (id: number) =>
  useQuery({ queryKey: ['escalas', id], queryFn: () => api<Escala>('GET', `/escalas/${id}/`) });

export type AcaoDeEscala =
  | { tipo: 'confirmar' }
  | { tipo: 'impedimento'; motivo: string }
  | { tipo: 'pedir-troca' }
  | { tipo: 'cancelar-troca' };

/** Confirmar, sinalizar impedimento, pedir ou cancelar troca: todas devolvem a escala atualizada. */
export function useAcaoDeEscala(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (acao: AcaoDeEscala) => {
      switch (acao.tipo) {
        case 'confirmar':
          return api<Escala>('POST', `/escalas/${id}/confirmar/`);
        case 'impedimento':
          return api<Escala>('POST', `/escalas/${id}/impedimento/`, { motivo: acao.motivo });
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
    queryFn: () => api<Evento[]>('GET', '/disponibilidades/eventos/'),
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
    onSuccess: (equipes) => queryClient.setQueryData(['equipes'], equipes),
  });
}
