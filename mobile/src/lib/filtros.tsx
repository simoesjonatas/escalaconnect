import Ionicons from '@expo/vector-icons/Ionicons';
import { addMonths, addWeeks, endOfMonth, endOfWeek, isWithinInterval, startOfMonth, startOfWeek } from 'date-fns';
import { ReactNode } from 'react';
import { Pressable, View } from 'react-native';

import { useTema } from './tema';
import { Cartao, Opcoes, Rotulo, Subtitulo, Suave } from './ui';

/** Uma opção de filtro: só aparece se separar parte da lista (nem nenhum item, nem todos). */
export type Filtro<T> = { valor: string; rotulo: string; aplica: (item: T) => boolean };

export const TODOS = 'todos';

/**
 * As opções úteis para esta lista e a escolhida (se ainda for útil; senão, nenhuma = todos).
 *
 * `porGrupo` (equipes): vale toda opção com algum item, mesmo que cubra a lista inteira, porque
 * escolher a equipe também troca as contagens mostradas; a linha só aparece com duas ou mais.
 */
export function escolher<T>(filtros: Filtro<T>[], itens: T[], valor: string, porGrupo = false) {
  let uteis = filtros.filter((f) => {
    const quantos = itens.filter(f.aplica).length;
    return quantos > 0 && (porGrupo || quantos < itens.length);
  });
  if (porGrupo && uteis.length < 2) uteis = [];
  return { uteis, ativo: uteis.find((f) => f.valor === valor) };
}

/** Aplica os filtros escolhidos, em sequência. */
export function aplicar<T>(itens: T[], ...ativos: (Filtro<T> | undefined)[]) {
  return ativos.reduce((lista, f) => (f ? lista.filter(f.aplica) : lista), itens);
}

/** Cartão "Filtrar …" com funil e "Limpar filtros" (mesmo visual do registro de disponibilidade). */
export function CaixaDeFiltros({
  titulo,
  filtrando,
  aoLimpar,
  children,
}: {
  titulo: string;
  filtrando: boolean;
  aoLimpar: () => void;
  children: ReactNode;
}) {
  const { cores } = useTema();
  return (
    <Cartao style={{ gap: 12 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <Ionicons name="funnel-outline" size={18} color={cores.texto} />
          <Subtitulo>{titulo}</Subtitulo>
        </View>
        {filtrando && (
          <Pressable onPress={aoLimpar} hitSlop={8} accessibilityRole="button">
            <Suave style={{ color: cores.primaria, fontWeight: '600' }}>Limpar filtros</Suave>
          </Pressable>
        )}
      </View>
      {children}
    </Cartao>
  );
}

/** Uma linha de filtro com título, para deixar claro o que as opções filtram. */
export function LinhaDeFiltro({
  titulo,
  opcoes,
  valor,
  ativas,
  aoEscolher,
}: {
  titulo: string;
  opcoes: { valor: string; rotulo: string }[];
  valor?: string;
  /** Para filtros de escolha múltipla (ex.: sábado e domingo). */
  ativas?: string[];
  aoEscolher: (valor: string) => void;
}) {
  return (
    <View style={{ gap: 6 }}>
      <Rotulo>{titulo}</Rotulo>
      <Opcoes opcoes={opcoes} valor={valor} ativas={ativas} aoEscolher={aoEscolher} />
    </View>
  );
}

/** Linha de filtro com "Todos" + as opções úteis; some quando não há o que filtrar. */
export function Chips<T>({
  titulo,
  todos,
  escolha,
  aoEscolher,
}: {
  titulo: string;
  todos: string;
  escolha: { uteis: Filtro<T>[]; ativo?: Filtro<T> };
  aoEscolher: (valor: string) => void;
}) {
  if (escolha.uteis.length === 0) return null;
  return (
    <LinhaDeFiltro
      titulo={titulo}
      opcoes={[{ valor: TODOS, rotulo: todos }, ...escolha.uteis.map((f) => ({ valor: f.valor, rotulo: f.rotulo }))]}
      valor={escolha.ativo?.valor ?? TODOS}
      aoEscolher={aoEscolher}
    />
  );
}

/** Uma opção por equipe que aparece na lista, em ordem alfabética. */
export function filtrosDeEquipe<T>(equipes: [number, string][], daEquipe: (item: T, id: number) => boolean): Filtro<T>[] {
  return [...new Map(equipes)]
    .sort(([, a], [, b]) => a.localeCompare(b))
    .map(([id, nome]) => ({ valor: String(id), rotulo: nome, aplica: (item: T) => daEquipe(item, id) }));
}

type Escolhas<T> = { uteis: Filtro<T>[]; ativo?: Filtro<T> };

/** Cartão de filtros com várias linhas e a contagem logo abaixo ("Mostrando 3 de 12 cultos"). */
export function CartaoDeFiltros<T>({
  titulo,
  nome,
  linhas,
  total,
  mostrando,
  aoLimpar,
}: {
  titulo: string;
  nome: string;
  linhas: { titulo: string; todos: string; escolha: Escolhas<T>; aoEscolher: (valor: string) => void }[];
  total: number;
  mostrando: number;
  aoLimpar: () => void;
}) {
  if (total === 0) return null;
  const filtrando = linhas.some((l) => l.escolha.ativo);
  return (
    <>
      {linhas.some((l) => l.escolha.uteis.length > 0) && (
        <CaixaDeFiltros titulo={titulo} filtrando={filtrando} aoLimpar={aoLimpar}>
          {linhas.map((linha) => (
            <Chips key={linha.titulo} {...linha} />
          ))}
        </CaixaDeFiltros>
      )}
      <Suave>{filtrando ? `Mostrando ${mostrando} de ${total} ${nome}` : `${total} ${nome}`}</Suave>
    </>
  );
}

const semana = (data: Date) => ({ start: startOfWeek(data, { weekStartsOn: 1 }), end: endOfWeek(data, { weekStartsOn: 1 }) });
const mes = (data: Date) => ({ start: startOfMonth(data), end: endOfMonth(data) });

/** Esta semana (segunda a domingo), a próxima, este mês e o próximo. */
export function filtrosDePeriodo<T>(dataDo: (item: T) => string): Filtro<T>[] {
  const hoje = new Date();
  const periodos = [
    { valor: 'semana', rotulo: 'Esta semana', intervalo: semana(hoje) },
    { valor: 'proxima-semana', rotulo: 'Próxima semana', intervalo: semana(addWeeks(hoje, 1)) },
    { valor: 'mes', rotulo: 'Este mês', intervalo: mes(hoje) },
    { valor: 'proximo-mes', rotulo: 'Próximo mês', intervalo: mes(addMonths(hoje, 1)) },
  ];
  return periodos.map(({ valor, rotulo, intervalo }) => ({
    valor,
    rotulo,
    aplica: (item: T) => isWithinInterval(new Date(dataDo(item)), intervalo),
  }));
}
