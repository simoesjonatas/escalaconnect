import { ReactNode } from 'react';
import { Pressable, Text, View } from 'react-native';

import { useTema } from './tema';
import { FuncaoDaEquipe, OpcoesDeEventos } from './types';
import { Cartao, Rotulo, Subtitulo, Suave } from './ui';

/** Liga/desliga um item numa lista de escolhas múltiplas. */
export const alternar = <T,>(lista: T[], item: T) =>
  lista.includes(item) ? lista.filter((i) => i !== item) : [...lista, item];

/** Chips que quebram linha (para escolhas múltiplas com vários itens, como funções e dias). */
export function ChipsDeEscolha<T extends string | number>({
  titulo,
  opcoes,
  ativas,
  aoTocar,
  dica,
}: {
  titulo: string;
  opcoes: { valor: T; rotulo: string }[];
  ativas: T[];
  aoTocar: (valor: T) => void;
  dica?: string;
}) {
  const { cores } = useTema();
  return (
    <View style={{ gap: 6 }}>
      {!!titulo && <Rotulo>{titulo}</Rotulo>}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
        {opcoes.map((opcao) => {
          const ativa = ativas.includes(opcao.valor);
          return (
            <Pressable
              key={String(opcao.valor)}
              onPress={() => aoTocar(opcao.valor)}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: ativa }}
              style={{
                paddingHorizontal: 14,
                paddingVertical: 8,
                borderRadius: 999,
                borderWidth: 1,
                borderColor: ativa ? cores.primaria : cores.borda,
                backgroundColor: ativa ? cores.primaria : cores.cartao,
              }}>
              <Text style={{ color: ativa ? cores.sobrePrimaria : cores.texto, fontSize: 14, fontWeight: '600' }}>
                {opcao.rotulo}
              </Text>
            </Pressable>
          );
        })}
      </View>
      {!!dica && <Suave style={{ fontSize: 13 }}>{dica}</Suave>}
    </View>
  );
}

/** Passo numerado de um formulário, como nas telas do site ("1 Evento", "2 Funções"...). */
export function Passo({
  numero,
  titulo,
  dica,
  children,
}: {
  numero: number;
  titulo: string;
  dica?: string;
  children: ReactNode;
}) {
  const { cores } = useTema();
  return (
    <Cartao style={{ gap: 14 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <View
          style={{
            width: 26,
            height: 26,
            borderRadius: 13,
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: cores.primaria,
          }}>
          <Text style={{ color: cores.sobrePrimaria, fontWeight: '800', fontSize: 13 }}>{numero}</Text>
        </View>
        <Subtitulo style={{ flex: 1 }}>{titulo}</Subtitulo>
      </View>
      {!!dica && <Suave style={{ marginTop: -6 }}>{dica}</Suave>}
      {children}
    </Cartao>
  );
}

/** Funções da equipe com "n de N marcadas" e "Marcar todas", como no "Gerar em Massa" do site. */
export function FuncoesDaEquipe({
  equipe,
  funcoes,
  aoMudar,
}: {
  equipe: (OpcoesDeEventos['equipes'])[number] | undefined;
  funcoes: number[];
  aoMudar: (ids: number[]) => void;
}) {
  const { cores } = useTema();
  if (!equipe) return <Suave>Escolha a equipe para ver as funções.</Suave>;
  if (!equipe.funcoes.length) return <Suave>Esta equipe ainda não tem funções cadastradas.</Suave>;
  const todas = equipe.funcoes.map((f: FuncaoDaEquipe) => f.id);
  const tudo = funcoes.length === todas.length;
  return (
    <View style={{ gap: 10 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Suave>
          {funcoes.length} de {todas.length} marcada{funcoes.length === 1 ? '' : 's'}
        </Suave>
        <Pressable onPress={() => aoMudar(tudo ? [] : todas)} hitSlop={8} accessibilityRole="button">
          <Text style={{ color: cores.primaria, fontWeight: '600' }}>{tudo ? 'Desmarcar todas' : 'Marcar todas'}</Text>
        </Pressable>
      </View>
      <ChipsDeEscolha
        titulo=""
        opcoes={equipe.funcoes.map((f) => ({ valor: f.id, rotulo: f.nome }))}
        ativas={funcoes}
        aoTocar={(id) => aoMudar(alternar(funcoes, id))}
      />
    </View>
  );
}
