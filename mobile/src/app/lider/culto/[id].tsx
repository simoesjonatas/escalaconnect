import { router, useLocalSearchParams } from 'expo-router';
import { Alert, Pressable, View } from 'react-native';

import { periodo } from '../../../lib/datas';
import { useCulto, usePedirConfirmacao } from '../../../lib/hooks';
import { Cores, useTema } from '../../../lib/tema';
import { EscalaDoCulto } from '../../../lib/types';
import { Botao, Cartao, Erro, Estado, Etiqueta, Suave, Subtitulo, Tela, Texto } from '../../../lib/ui';

function situacao(escala: EscalaDoCulto, cores: Cores): { texto: string; cor: string } {
  if (!escala.pessoa) return { texto: 'Vaga em aberto', cor: cores.pendente };
  if (escala.tem_impedimento) return { texto: 'Impedimento', cor: cores.perigo };
  if (escala.troca_pendente) return { texto: 'Troca pedida', cor: cores.neutra };
  if (escala.confirmada) return { texto: 'Confirmada', cor: cores.confirmada };
  return { texto: 'A confirmar', cor: cores.pendente };
}

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

  function pedirConfirmacao() {
    Alert.alert(
      'Pedir confirmação',
      `${faltam === 1 ? '1 pessoa ainda não confirmou' : `${faltam} pessoas ainda não confirmaram`}. Elas recebem um aviso no app e por e-mail.`,
      [
        { text: 'Voltar', style: 'cancel' },
        {
          text: 'Enviar',
          onPress: () =>
            pedir.mutate(undefined, {
              onSuccess: ({ pendentes }) =>
                Alert.alert('Pedido enviado', pendentes ? 'Quem falta vai receber o pedido de confirmação.' : 'Todos já confirmaram.'),
            }),
        },
      ],
    );
  }

  return (
    <Tela atualizando={consulta.isRefetching} aoAtualizar={() => consulta.refetch()}>
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
            <Botao
              titulo={`Pedir confirmação (${faltam})`}
              carregando={pedir.isPending}
              aoTocar={pedirConfirmacao}
            />
          )}

          {equipes.map((equipe) => (
            <View key={equipe} style={{ gap: 12 }}>
              {equipes.length > 1 && <Subtitulo style={{ marginTop: 8 }}>{equipe}</Subtitulo>}
              {escalas
                .filter((e) => e.equipe === equipe)
                .map((escala) => {
                  const cartao = (
                    <Cartao>
                      <Etiqueta {...situacao(escala, cores)} />
                      <Subtitulo>{escala.funcao}</Subtitulo>
                      {escala.pessoa ? (
                        <Texto>{escala.pessoa.nome}</Texto>
                      ) : (
                        <Suave>Tocar para escalar alguém</Suave>
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
