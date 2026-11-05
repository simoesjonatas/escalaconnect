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

/** "março de 2025" */
export const mesEAno = (data: Date | string) => fmt(data, "MMMM 'de' yyyy");

/** "Outubro" (com o ano quando não for o ano corrente: "Janeiro 2027"). */
export function mesPorExtenso(data: Date | string): string {
  const d = new Date(data);
  const nome = fmt(d, 'MMMM');
  const texto = nome.charAt(0).toUpperCase() + nome.slice(1);
  return d.getFullYear() === new Date().getFullYear() ? texto : `${texto} ${d.getFullYear()}`;
}

/** "07011996" -> "07/01/1996", conforme a pessoa digita. */
export function mascaraDeData(texto: string) {
  const digitos = texto.replace(/\D/g, '').slice(0, 8);
  return [digitos.slice(0, 2), digitos.slice(2, 4), digitos.slice(4)].filter(Boolean).join('/');
}

/** "07/01/1996" -> "1996-01-07"; null enquanto incompleta. */
export function dataIso(texto: string) {
  const partes = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(texto);
  return partes ? `${partes[3]}-${partes[2]}-${partes[1]}` : null;
}

/** "12345678909" -> "123.456.789-09", conforme a pessoa digita. */
export function mascaraDeCpf(texto: string) {
  const d = texto.replace(/\D/g, '').slice(0, 11);
  return [d.slice(0, 3), d.slice(3, 6), d.slice(6, 9)].filter(Boolean).join('.') + (d.length > 9 ? `-${d.slice(9)}` : '');
}
