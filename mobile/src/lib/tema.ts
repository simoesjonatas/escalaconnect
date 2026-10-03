import { useColorScheme } from 'react-native';

/** Paleta do app. O verde é o da marca Connect (o mesmo do site), sobre fundo escuro ou claro. */
export type Cores = {
  fundo: string;
  cartao: string;
  borda: string;
  texto: string;
  textoSuave: string;
  primaria: string;
  sobrePrimaria: string;
  confirmada: string;
  pendente: string;
  neutra: string;
  perigo: string;
};

export const escuro: Cores = {
  fundo: '#111214',
  cartao: '#1b1d21',
  borda: '#2b2f36',
  texto: '#f2f4f5',
  textoSuave: '#9aa4ad',
  primaria: '#39ff14',
  sobrePrimaria: '#0b1a05',
  confirmada: '#4caf50',
  pendente: '#ffa726',
  neutra: '#64b5f6',
  perigo: '#ef5350',
};

export const claro: Cores = {
  fundo: '#f4f6f8',
  cartao: '#ffffff',
  borda: '#e2e6ea',
  texto: '#1c2430',
  textoSuave: '#667085',
  primaria: '#1f9d55',
  sobrePrimaria: '#ffffff',
  confirmada: '#2e7d32',
  pendente: '#ef6c00',
  neutra: '#3b5bdb',
  perigo: '#c62828',
};

/** Cores do tema atual, seguindo o modo claro/escuro do aparelho. */
export function useTema(): { cores: Cores; escuro: boolean } {
  const esquema = useColorScheme();
  const ehEscuro = esquema !== 'light';
  return { cores: ehEscuro ? escuro : claro, escuro: ehEscuro };
}

export const espaco = { p: 8, m: 12, g: 16, gg: 24 };
