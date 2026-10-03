import { TipoPeriodo } from './types';

/** Textos de cada tipo de período (as telas são as mesmas para os dois). */
export const textosDoPeriodo: Record<TipoPeriodo, { singular: string; plural: string; vazio: string }> = {
  disponibilidades: {
    singular: 'disponibilidade',
    plural: 'Disponibilidades',
    vazio: 'Você ainda não informou quando pode servir.',
  },
  indisponibilidades: {
    singular: 'indisponibilidade',
    plural: 'Indisponibilidades',
    vazio: 'Nenhum período em que você não pode servir.',
  },
};

export const tipoDoParametro = (tipo?: string): TipoPeriodo =>
  tipo === 'indisponibilidades' ? 'indisponibilidades' : 'disponibilidades';
