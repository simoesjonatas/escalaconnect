import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable } from 'react-native';

import { periodo } from '../../../lib/datas';
import { useEscalarNaVaga, useVaga } from '../../../lib/hooks';
import { useTema } from '../../../lib/tema';
import { Candidato } from '../../../lib/types';
import { Campo, Cartao, Erro, Estado, Etiqueta, Suave, Subtitulo, Tela, Texto } from '../../../lib/ui';

const semAcento = (texto: string) =>
  texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

/** Escolher quem ocupa uma vaga em aberto: disponíveis primeiro, depois os demais membros da equipe. */
export default function EscalarNaVaga() {
  const id = Number(useLocalSearchParams<{ id: string }>().id);
  const consulta = useVaga(id);
  const escalar = useEscalarNaVaga(id);
  const [busca, setBusca] = useState('');
  const { cores } = useTema();
  const dados = consulta.data;

  const candidatos = (dados?.candidatos ?? []).filter((c) => semAcento(c.nome).includes(semAcento(busca.trim())));

  function confirmar(candidato: Candidato) {
    const aviso = candidato.disponivel ? '' : '\n\nEssa pessoa não marcou disponibilidade para este evento.';
    Alert.alert('Escalar', `Escalar ${candidato.nome} nesta vaga? A pessoa recebe um aviso no app.${aviso}`, [
      { text: 'Voltar', style: 'cancel' },
      {
        text: 'Escalar',
        onPress: () =>
          escalar.mutate(candidato.id, {
            onSuccess: () => {
              Alert.alert('Pronto', `${candidato.nome} está na escala e recebeu um aviso no app.`);
              router.back();
            },
          }),
      },
    ]);
  }

  return (
    <Tela atualizando={consulta.isRefetching} aoAtualizar={() => consulta.refetch()}>
      <Estado consulta={consulta} />
      {dados && (
        <>
          <Cartao>
            <Etiqueta texto="Vaga em aberto" cor={cores.pendente} />
            <Subtitulo>{dados.vaga.evento.nome}</Subtitulo>
            <Texto>{periodo(dados.vaga.evento.data_inicio, dados.vaga.evento.data_fim)}</Texto>
            <Suave>
              {dados.vaga.funcao} · {dados.vaga.equipe}
            </Suave>
          </Cartao>

          <Erro erro={escalar.error} />

          {dados.candidatos.length > 6 && (
            <Campo rotulo="Buscar pessoa" value={busca} onChangeText={setBusca} placeholder="Nome" autoCorrect={false} />
          )}

          {candidatos.length === 0 && (
            <Suave style={{ textAlign: 'center' }}>
              {busca ? 'Ninguém encontrado com esse nome.' : 'Todos os membros da equipe já estão escalados neste evento.'}
            </Suave>
          )}

          {candidatos.map((candidato) => (
            <Pressable
              key={candidato.id}
              onPress={() => confirmar(candidato)}
              disabled={escalar.isPending}
              accessibilityRole="button"
              style={({ pressed }) => (pressed || escalar.isPending) && { opacity: 0.6 }}>
              <Cartao>
                <Subtitulo>{candidato.nome}</Subtitulo>
                <Texto style={{ color: candidato.disponivel ? cores.confirmada : cores.textoSuave, fontWeight: '600' }}>
                  {candidato.disponivel ? 'Disponível' : 'Sem disponibilidade marcada'}
                </Texto>
                <Suave>
                  {candidato.servicos_no_mes === 0
                    ? 'Ainda não serve neste mês'
                    : `Já serve ${candidato.servicos_no_mes}x neste mês`}
                </Suave>
              </Cartao>
            </Pressable>
          ))}
        </>
      )}
    </Tela>
  );
}
