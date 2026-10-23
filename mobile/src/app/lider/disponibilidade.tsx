import { addMonths } from 'date-fns';
import { useState } from 'react';
import { Alert, View } from 'react-native';

import { mesPorExtenso } from '../../lib/datas';
import { PedidoDeDisponibilidade, useDisponibilidadeDaEquipe, usePedirDisponibilidade } from '../../lib/hooks';
import { Botao, Cartao, Erro, Estado, Opcoes, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

/** Este mês e os dois seguintes, no formato da API (ano e mês 1–12). */
const MESES = [0, 1, 2].map((n) => {
  const data = addMonths(new Date(), n);
  return { valor: `${data.getFullYear()}-${data.getMonth() + 1}`, rotulo: mesPorExtenso(data) };
});

/** Mostra quem da equipe ainda não marcou disponibilidade no mês e pede (só app, ou e-mail e app). */
export default function PedirDisponibilidade() {
  const [equipe, setEquipe] = useState<number>();
  const [mes, setMes] = useState(MESES[1].valor); // padrão: próximo mês, como no servidor
  const [ano, numeroDoMes] = mes.split('-').map(Number);
  const consulta = useDisponibilidadeDaEquipe({ equipe, ano, mes: numeroDoMes });
  const pedir = usePedirDisponibilidade();
  const dados = consulta.data;
  const nomeDoMes = MESES.find((m) => m.valor === mes)?.rotulo.toLowerCase() ?? '';

  function enviar(canal: PedidoDeDisponibilidade['canal']) {
    if (!dados?.equipe_id) return;
    const pedido = { equipe_id: dados.equipe_id, ano, mes: numeroDoMes, canal };
    const porOnde = canal === 'app' ? 'um aviso no app' : 'um aviso no app e um e-mail';
    Alert.alert('Pedir disponibilidade', `Quem ainda não marcou ${nomeDoMes} recebe ${porOnde}.`, [
      { text: 'Voltar', style: 'cancel' },
      {
        text: 'Enviar',
        onPress: () =>
          pedir.mutate(pedido, {
            onSuccess: ({ faltantes }) =>
              Alert.alert(
                'Pedido enviado',
                faltantes ? 'Quem ainda não marcou vai receber o pedido.' : 'Todos da equipe já marcaram disponibilidade.',
              ),
          }),
      },
    ]);
  }

  return (
    <Tela aoAtualizar={() => consulta.refetch()}>
      {dados && dados.equipes.length > 1 && (
        <Opcoes
          opcoes={dados.equipes.map((e) => ({ valor: String(e.id), rotulo: e.nome }))}
          valor={String(dados.equipe_id)}
          aoEscolher={(valor) => setEquipe(Number(valor))}
        />
      )}
      <Opcoes opcoes={MESES} valor={mes} aoEscolher={setMes} />

      <Estado consulta={consulta} />
      {dados && (
        <>
          <Cartao>
            <Subtitulo>
              {dados.faltantes.length === 0
                ? 'Todos já marcaram 🙌'
                : `${dados.faltantes.length} de ${dados.membros} ainda não marcaram`}
            </Subtitulo>
            {dados.faltantes.length === 0 ? (
              <Suave>Ninguém da equipe está sem disponibilidade em {nomeDoMes}.</Suave>
            ) : (
              dados.faltantes.map((pessoa) => <Texto key={pessoa.id}>{pessoa.nome}</Texto>)
            )}
          </Cartao>

          <Erro erro={pedir.error} />
          {dados.faltantes.length > 0 && (
            <View style={{ gap: 8 }}>
              <Botao titulo="Pedir pelo app" carregando={pedir.isPending && pedir.variables?.canal === 'app'} aoTocar={() => enviar('app')} />
              <Botao
                titulo="Pedir pelo app e por e-mail"
                variante="secundario"
                carregando={pedir.isPending && pedir.variables?.canal === 'todos'}
                aoTocar={() => enviar('todos')}
              />
              <Suave>Só quem ainda não marcou nada em {nomeDoMes} recebe o pedido.</Suave>
            </View>
          )}
        </>
      )}
    </Tela>
  );
}
