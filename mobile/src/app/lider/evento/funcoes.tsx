import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, View } from 'react-native';

import { periodo } from '../../../lib/datas';
import { alternar, ChipsDeEscolha, Passo } from '../../../lib/formulario-lider';
import { LinhaDeFiltro } from '../../../lib/filtros';
import { useAplicarFuncoes, useEventosEditaveis, useOpcoesDeEventos } from '../../../lib/hooks';
import { useTema } from '../../../lib/tema';
import { EventoEditavel } from '../../../lib/types';
import { Botao, Cartao, Erro, Estado, Subtitulo, Suave, Tela } from '../../../lib/ui';

const EXIBIR = [
  { valor: 'todos', rotulo: 'Todos' },
  { valor: 'equipe', rotulo: 'Da equipe' },
  { valor: 'publicos', rotulo: 'Somente públicos' },
];

/** Mesmo "Funções em Eventos" do site: escolhe as funções e os eventos; cada par vira uma vaga. */
export default function FuncoesEmEventos() {
  const opcoes = useOpcoesDeEventos();
  const eventos = useEventosEditaveis();
  const aplicar = useAplicarFuncoes();
  const { cores } = useTema();
  const [funcoes, setFuncoes] = useState<number[]>([]);
  const [marcados, setMarcados] = useState<number[]>([]);
  const [exibir, setExibir] = useState('todos');

  const equipes = opcoes.data?.equipes ?? [];
  const nomeDaFuncao = new Map(equipes.flatMap((e) => e.funcoes.map((f) => [f.id, f.nome] as const)));
  const lista = (eventos.data ?? []).filter(
    (e) => exibir === 'todos' || (exibir === 'publicos' ? !e.equipe_id : !!e.equipe_id),
  );
  const todosMarcados = lista.length > 0 && lista.every((e) => marcados.includes(e.id));

  function alternarTodos() {
    const ids = lista.map((e) => e.id);
    setMarcados(todosMarcados ? marcados.filter((id) => !ids.includes(id)) : [...new Set([...marcados, ...ids])]);
  }

  /** "Já tem: Porta" quando o evento já tem alguma das funções escolhidas (essas são puladas). */
  function jaTem(evento: EventoEditavel) {
    const repetidas = funcoes.filter((f) => evento.funcao_ids.includes(f));
    if (!repetidas.length) return null;
    return repetidas.length === funcoes.length
      ? 'Já tem essas funções'
      : `Já tem: ${repetidas.map((f) => nomeDaFuncao.get(f)).join(', ')}`;
  }

  function adicionar() {
    aplicar.mutate(
      { evento_ids: marcados, funcao_ids: funcoes },
      {
        onSuccess: ({ criadas, existentes }) => {
          Alert.alert(
            'Pronto',
            `${criadas} vaga${criadas === 1 ? '' : 's'} adicionada${criadas === 1 ? '' : 's'}.` +
              (existentes ? ` ${existentes} já existia${existentes === 1 ? '' : 'm'} e ficou${existentes === 1 ? '' : 'ram'} como estava${existentes === 1 ? '' : 'm'}.` : ''),
          );
          router.back();
        },
      },
    );
  }

  return (
    <Tela aoAtualizar={() => eventos.refetch()}>
      <Estado consulta={opcoes} />
      {opcoes.data && (
        <>
          <Passo numero={1} titulo="Funções" dica="Cada função escolhida vira uma vaga em aberto em cada evento marcado.">
            {equipes.every((e) => !e.funcoes.length) && <Suave>Suas equipes ainda não têm funções cadastradas.</Suave>}
            {equipes
              .filter((e) => e.funcoes.length)
              .map((e) => (
                <ChipsDeEscolha
                  key={e.id}
                  titulo={equipes.length > 1 ? e.nome : ''}
                  opcoes={e.funcoes.map((f) => ({ valor: f.id, rotulo: f.nome }))}
                  ativas={funcoes}
                  aoTocar={(id) => setFuncoes(alternar(funcoes, id))}
                />
              ))}
          </Passo>

          <Passo numero={2} titulo="Eventos">
            <LinhaDeFiltro titulo="Exibir eventos" opcoes={EXIBIR} valor={exibir} aoEscolher={setExibir} />
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
              <Suave>
                {marcados.length} selecionado{marcados.length === 1 ? '' : 's'}
              </Suave>
              {lista.length > 0 && (
                <Pressable onPress={alternarTodos} hitSlop={8} accessibilityRole="button">
                  <Suave style={{ color: cores.primaria, fontWeight: '600' }}>
                    {todosMarcados ? 'Desmarcar todos' : 'Marcar todos'}
                  </Suave>
                </Pressable>
              )}
            </View>
          </Passo>

          <Erro erro={aplicar.error} />
          <Botao
            titulo={
              marcados.length && funcoes.length
                ? `Adicionar ${funcoes.length} funç${funcoes.length === 1 ? 'ão' : 'ões'} a ${marcados.length} evento${marcados.length === 1 ? '' : 's'}`
                : 'Adicionar funções aos eventos'
            }
            desabilitado={!marcados.length || !funcoes.length}
            carregando={aplicar.isPending}
            aoTocar={adicionar}
          />

          <Estado consulta={eventos} vazio={lista.length === 0 && 'Nenhum evento futuro para mostrar.'} />
          {lista.map((evento) => {
            const marcado = marcados.includes(evento.id);
            const aviso = jaTem(evento);
            return (
              <Pressable
                key={evento.id}
                onPress={() => setMarcados(alternar(marcados, evento.id))}
                accessibilityRole="checkbox"
                accessibilityState={{ checked: marcado }}>
                <Cartao style={marcado ? { borderColor: cores.primaria } : undefined}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                    <Ionicons
                      name={marcado ? 'checkbox' : 'square-outline'}
                      size={26}
                      color={marcado ? cores.primaria : cores.textoSuave}
                    />
                    <View style={{ flex: 1, gap: 2 }}>
                      <Subtitulo>{evento.nome}</Subtitulo>
                      <Suave>{periodo(evento.data_inicio, evento.data_fim)}</Suave>
                      <Suave>{evento.equipe ?? 'Público'}</Suave>
                      {!!aviso && <Suave style={{ color: cores.pendente }}>{aviso}</Suave>}
                    </View>
                  </View>
                </Cartao>
              </Pressable>
            );
          })}

        </>
      )}
    </Tela>
  );
}
