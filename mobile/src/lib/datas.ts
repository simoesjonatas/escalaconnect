import { format, isSameDay } from 'date-fns';
import { ptBR } from 'date-fns/locale';

const fmt = (data: Date | string, padrao: string) => format(new Date(data), padrao, { locale: ptBR });

/** "domingo, 4 de outubro" */
export const diaPorExtenso = (data: Date | string) => fmt(data, "EEEE, d 'de' MMMM");

/** "19:00" */
export const hora = (data: Date | string) => fmt(data, 'HH:mm');

/** "dom 04/10 · 19:00" (listas compactas) */
export const diaCurto = (data: Date | string) => `${fmt(data, 'EEEE').slice(0, 3)} ${fmt(data, "dd/MM '·' HH:mm")}`;

/** "04/10 19:00" */
export const diaEHora = (data: Date | string) => fmt(data, 'dd/MM HH:mm');

/** "domingo, 4 de outubro · 19:00 – 21:00" (com a data final quando termina em outro dia). */
export function periodo(inicio: string, fim: string): string {
  const ate = isSameDay(new Date(inicio), new Date(fim)) ? hora(fim) : diaEHora(fim);
  return `${diaPorExtenso(inicio)} · ${hora(inicio)} – ${ate}`;
}

/** "2026-10-04", no fuso do aparelho (chave dos dias no calendário). */
export const chaveDoDia = (data: Date | string) => fmt(data, 'yyyy-MM-dd');

/** "Outubro" (com o ano quando não for o ano corrente: "Janeiro 2027"). */
export function mesPorExtenso(data: Date | string): string {
  const d = new Date(data);
  const nome = fmt(d, 'MMMM');
  const texto = nome.charAt(0).toUpperCase() + nome.slice(1);
  return d.getFullYear() === new Date().getFullYear() ? texto : `${texto} ${d.getFullYear()}`;
}
