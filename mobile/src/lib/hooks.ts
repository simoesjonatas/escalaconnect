import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './api';
import { Equipes, Escala, Evento, EventoCalendario, Home, Periodo, TipoPeriodo } from './types';

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

export const usePeriodos = (tipo: TipoPeriodo) =>
  useQuery({ queryKey: ['periodos', tipo], queryFn: () => api<Periodo[]>('GET', `/${tipo}/`) });

export const useEventosElegiveis = (tipo: TipoPeriodo) =>
  useQuery({ queryKey: ['periodos', tipo, 'eventos'], queryFn: () => api<Evento[]>('GET', `/${tipo}/eventos/`) });

export type MudancaDePeriodo =
  | { acao: 'criar'; data_inicio: string; data_fim: string }
  | { acao: 'por-evento'; evento_ids: number[] }
  | { acao: 'excluir'; id: number };

export function useMudarPeriodos(tipo: TipoPeriodo) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mudanca: MudancaDePeriodo) => {
      switch (mudanca.acao) {
        case 'criar':
          return api('POST', `/${tipo}/`, { data_inicio: mudanca.data_inicio, data_fim: mudanca.data_fim });
        case 'por-evento':
          return api('POST', `/${tipo}/por-evento/`, { evento_ids: mudanca.evento_ids });
        case 'excluir':
          return api('DELETE', `/${tipo}/${mudanca.id}/`);
      }
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['periodos'] });
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
