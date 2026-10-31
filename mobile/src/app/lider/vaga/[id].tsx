import { router, Stack, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable } from 'react-native';

import { periodo } from '../../../lib/datas';
import { useAcaoDoLider, useEscalarNaVaga, useVaga } from '../../../lib/hooks';
import { useTema } from '../../../lib/tema';
import { Candidato } from '../../../lib/types';
import { Campo, Cartao, Erro, Estado, Etiqueta, Grupo, ItemDeGrupo, Rotulo, Suave, Subtitulo, Tela, Texto } from '../../../lib/ui';

const semAcento = (texto: string) =>
  texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

/**
 * Escolher quem ocupa uma vaga em aberto: disponíveis primeiro, depois os demais membros da equipe.
 * Com impedimento ou troca à espera, o líder vê quem pode substituir antes de decidir: escolher
 * alguém aprova o pedido e escala a pessoa de uma vez. Se quem está ainda não confirmou, escolher
 * alguém troca a pessoa (quem sai recebe um aviso).
 */
export default function EscalarNaVaga() {
  const id = Number(useLocalSearchParams<{ id: string }>().id);
  const consulta = useVaga(id);
  const escalar = useEscalarNaVaga(id);
  const acao = useAcaoDoLider();
  const [busca, setBusca] = useState('');
  const { cores } = useTema();
  const dados = consulta.data;

  const candidatos = (dados?.candidatos ?? []).filter((c) => semAcento(c.nome).includes(semAcento(busca.trim())));
  const pedido = dados?.pedido;
  // Está na escala e ainda não confirmou (sem pedido à espera): o líder pode trocar.
  const aConfirmar = !pedido ? dados?.pessoa : null;
  const nomeDoPedido = pedido?.tipo === 'impedimentos' ? 'o impedimento' : 'a troca';
  const ocupado = escalar.isPending || acao.isPending;

  function confirmar(candidato: Candidato) {
    const aviso =
      candidato.disponivel || candidato.se_ofereceu ? '' : '\n\nEssa pessoa não marcou disponibilidade para este evento.';
    const pergunta = pedido
      ? `Aprovar ${nomeDoPedido} de ${pedido.pessoa.nome} e escalar ${candidato.nome} no lugar? Os dois recebem um aviso no app.`
      : aConfirmar
        ? `Tirar ${aConfirmar.nome} e escalar ${candidato.nome} no lugar? Os dois recebem um aviso no app.`
        : `Escalar ${candidato.nome} nesta vaga? A pessoa recebe um aviso no app.`;
    Alert.alert(aConfirmar ? 'Trocar pessoa' : 'Escalar', `${pergunta}${aviso}`, [
      { text: 'Voltar', style: 'cancel' },
      {
        text: aConfirmar ? 'Trocar' : 'Escalar',
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

  /** Decidir o pedido sem escolher substituto: aprovar deixa a vaga aberta aqui mesmo; recusar volta. */
  function decidir(qual: 'aprovar' | 'recusar') {
    if (!pedido) return;
    const aprovar = qual === 'aprovar';
    Alert.alert(
      aprovar ? 'Aprovar sem substituto' : 'Recusar pedido',
      aprovar
        ? `${pedido.pessoa.nome} sai da escala e a vaga fica aberta.`
        : `${pedido.pessoa.nome} continua escalado e será avisado.`,
      [
        { text: 'Voltar', style: 'cancel' },
        {
          text: aprovar ? 'Aprovar' : 'Recusar',
          style: aprovar ? 'default' : 'destructive',
          onPress: () =>
            acao.mutate(
              { tipo: pedido.tipo, id: pedido.id, acao: qual },
              { onSuccess: () => (aprovar ? void consulta.refetch() : router.back()) },
            ),
        },
      ],
    );
  }

  return (
    <Tela aoAtualizar={() => consulta.refetch()}>
      <Stack.Screen options={{ title: pedido || aConfirmar ? 'Quem pode substituir' : 'Escalar na vaga' }} />
      <Estado consulta={consulta} />
      {dados && (
        <>
          <Cartao>
            {pedido ? (
              <Etiqueta
                texto={pedido.tipo === 'impedimentos' ? 'Impedimento' : 'Troca pedida'}
                cor={pedido.tipo === 'impedimentos' ? cores.perigo : cores.neutra}
              />
            ) : aConfirmar ? (
              <Etiqueta texto="A confirmar" cor={cores.pendente} />
            ) : (
              <Etiqueta texto="Vaga em aberto" cor={cores.pendente} />
            )}
            <Subtitulo>{dados.vaga.evento.nome}</Subtitulo>
            <Texto>{periodo(dados.vaga.evento.data_inicio, dados.vaga.evento.data_fim)}</Texto>
            <Suave>
              {dados.vaga.funcao} · {dados.vaga.equipe}
              {pedido ? ` · ${pedido.pessoa.nome}` : aConfirmar ? ` · ${aConfirmar.nome}` : ''}
            </Suave>
            {!!pedido?.motivo && <Texto>Motivo: {pedido.motivo}</Texto>}
            {aConfirmar && <Texto>{aConfirmar.nome} ainda não confirmou. Se quiser, escolha outra pessoa abaixo.</Texto>}
          </Cartao>

          {pedido && (
            <Grupo titulo="Decidir sem substituto">
              <ItemDeGrupo
                icone="checkmark-circle-outline"
                titulo="Aprovar e deixar a vaga aberta"
                carregando={acao.isPending && acao.variables?.acao === 'aprovar'}
                aoTocar={() => !ocupado && decidir('aprovar')}
              />
              <ItemDeGrupo
                icone="close-circle-outline"
                titulo={`Recusar ${nomeDoPedido}`}
                perigo
                carregando={acao.isPending && acao.variables?.acao === 'recusar'}
                aoTocar={() => !ocupado && decidir('recusar')}
              />
            </Grupo>
          )}

          <Erro erro={escalar.error ?? acao.error} />

          {(pedido || aConfirmar) && (
            <Rotulo style={{ marginTop: 4, marginLeft: 4 }}>
              {pedido ? 'Quem pode substituir · tocar aprova e escala' : 'Quem pode substituir · tocar troca a pessoa'}
            </Rotulo>
          )}

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
              disabled={ocupado}
              accessibilityRole="button"
              style={({ pressed }) => (pressed || ocupado) && { opacity: 0.6 }}>
              <Cartao>
                {candidato.se_ofereceu && <Etiqueta texto="Se ofereceu" cor={cores.confirmada} />}
                <Subtitulo>{candidato.nome}</Subtitulo>
                {/* Quem se ofereceu para a vaga já disse que pode, mesmo sem ter marcado disponibilidade. */}
                <Texto
                  style={{
                    color: candidato.disponivel || candidato.se_ofereceu ? cores.confirmada : cores.textoSuave,
                    fontWeight: '600',
                  }}>
                  {candidato.disponivel
                    ? 'Disponível'
                    : candidato.se_ofereceu
                      ? 'Quer servir nesta vaga'
                      : 'Sem disponibilidade marcada'}
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
