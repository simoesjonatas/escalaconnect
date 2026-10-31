import { router, useLocalSearchParams } from 'expo-router';
import { Alert, Pressable, View } from 'react-native';

import { periodo } from '../../../lib/datas';
import { CanalDoPedido, useCulto, usePedirConfirmacao } from '../../../lib/hooks';
import { Cores, useTema } from '../../../lib/tema';
import { EscalaDoCulto } from '../../../lib/types';
import { Botao, Cartao, Erro, Estado, Etiqueta, Suave, Subtitulo, Tela, Texto } from '../../../lib/ui';

function situacao(escala: EscalaDoCulto, cores: Cores): { texto: string; cor: string } {
  const ofertas = escala.ofertas?.length ?? 0;
  if (!escala.pessoa && ofertas) {
    return { texto: ofertas === 1 ? '1 quer servir' : `${ofertas} querem servir`, cor: cores.confirmada };
  }
  if (!escala.pessoa) return { texto: 'Vaga em aberto', cor: cores.pendente };
  if (escala.tem_impedimento) return { texto: 'Impedimento', cor: cores.perigo };
  if (escala.troca_pendente) return { texto: 'Troca pedida', cor: cores.neutra };
  if (escala.confirmada) return { texto: 'Confirmada', cor: cores.confirmada };
  return { texto: 'A confirmar', cor: cores.pendente };
}

/** O que pede ação vem primeiro: vagas com alguém querendo servir, depois as demais vagas. */
const prioridade = (e: EscalaDoCulto) => (e.pessoa ? 2 : e.ofertas?.length ? 0 : 1);

/** Um culto visto pelo líder: quem confirmou, quem falta e as vagas das equipes que ele lidera. */
export default function CultoDoLider() {
  const id = Number(useLocalSearchParams<{ id: string }>().id);
  const consulta = useCulto(id);
  const pedir = usePedirConfirmacao(id);
  const { cores } = useTema();
  const dados = consulta.data;

  const escalas = dados?.escalas ?? [];
  const faltam = escalas.filter((e) => e.pessoa && !e.confirmada).length;
  const confirmadas = escalas.filter((e) => e.pessoa && e.confirmada).length;
  const vagas = escalas.filter((e) => !e.pessoa).length;
  const equipes = [...new Set(escalas.map((e) => e.equipe))];

  function pedirConfirmacao(canal: CanalDoPedido) {
    const porOnde = canal === 'app' ? 'um aviso no app' : 'um aviso no app e um e-mail';
    Alert.alert(
      'Pedir confirmação',
      `${faltam === 1 ? '1 pessoa ainda não confirmou e recebe' : `${faltam} pessoas ainda não confirmaram e recebem`} ${porOnde}.`,
      [
        { text: 'Voltar', style: 'cancel' },
        {
          text: 'Enviar',
          onPress: () =>
            pedir.mutate(canal, {
              onSuccess: ({ pendentes }) =>
                Alert.alert('Pedido enviado', pendentes ? 'Quem falta vai receber o pedido de confirmação.' : 'Todos já confirmaram.'),
            }),
        },
      ],
    );
  }

  return (
    <Tela aoAtualizar={() => consulta.refetch()}>
      <Estado consulta={consulta} />
      {dados && (
        <>
          <Cartao>
            <Subtitulo>{dados.evento.nome}</Subtitulo>
            <Texto>{periodo(dados.evento.data_inicio, dados.evento.data_fim)}</Texto>
            <Suave>
              {confirmadas} confirmada{confirmadas === 1 ? '' : 's'} · {faltam} a confirmar · {vagas} vaga{vagas === 1 ? '' : 's'}
            </Suave>
          </Cartao>

          <Erro erro={pedir.error} />
          {faltam > 0 && (
            <View style={{ gap: 8 }}>
              <Botao
                titulo={`Pedir confirmação pelo app (${faltam})`}
                carregando={pedir.isPending && pedir.variables === 'app'}
                aoTocar={() => pedirConfirmacao('app')}
              />
              <Botao
                titulo="Pedir pelo app e por e-mail"
                variante="secundario"
                carregando={pedir.isPending && pedir.variables === 'todos'}
                aoTocar={() => pedirConfirmacao('todos')}
              />
            </View>
          )}

          {equipes.map((equipe) => (
            <View key={equipe} style={{ gap: 12 }}>
              {equipes.length > 1 && <Subtitulo style={{ marginTop: 8 }}>{equipe}</Subtitulo>}
              {escalas
                .filter((e) => e.equipe === equipe)
                .sort((a, b) => prioridade(a) - prioridade(b))
                .map((escala) => {
                  const cartao = (
                    <Cartao>
                      <Etiqueta {...situacao(escala, cores)} />
                      <Subtitulo>{escala.funcao}</Subtitulo>
                      {escala.pessoa ? (
                        <Texto>{escala.pessoa.nome}</Texto>
                      ) : (
                        <>
                          {!!escala.ofertas?.length && (
                            <Texto>Se ofereceram: {escala.ofertas.map((p) => p.nome).join(', ')}</Texto>
                          )}
                          <Suave>
                            {escala.disponiveis == null
                              ? 'Tocar para escalar alguém'
                              : `${escala.disponiveis === 0 ? 'Ninguém marcou disponibilidade' : `${escala.disponiveis} ${escala.disponiveis === 1 ? 'disponível' : 'disponíveis'}`} · Tocar para escalar`}
                          </Suave>
                        </>
                      )}
                    </Cartao>
                  );
                  return escala.pessoa ? (
                    <View key={escala.id}>{cartao}</View>
                  ) : (
                    <Pressable
                      key={escala.id}
                      accessibilityRole="button"
                      onPress={() => router.push({ pathname: '/lider/vaga/[id]', params: { id: escala.id } })}>
                      {cartao}
                    </Pressable>
                  );
                })}
            </View>
          ))}
        </>
      )}
    </Tela>
  );
}
