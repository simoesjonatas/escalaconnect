import { addMonths } from 'date-fns';
import { useState } from 'react';
import { Alert, View } from 'react-native';

import { mesPorExtenso } from '../../lib/datas';
import { LinhaDeFiltro } from '../../lib/filtros';
import { PedidoDeDisponibilidade, useDisponibilidadeDaEquipe, usePedirDisponibilidade } from '../../lib/hooks';
import { useTema } from '../../lib/tema';
import { Avatar, Botao, Cartao, Erro, Estado, Rotulo, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

/** Este mês e os dois seguintes, no formato da API (ano e mês 1–12). */
const MESES = [0, 1, 2].map((n) => {
  const data = addMonths(new Date(), n);
  return { valor: `${data.getFullYear()}-${data.getMonth() + 1}`, rotulo: mesPorExtenso(data) };
});

/** Quantos já marcaram, em barra. */
function Progresso({ feito, total }: { feito: number; total: number }) {
  const { cores } = useTema();
  const fracao = total ? feito / total : 1;
  return (
    <View style={{ height: 8, borderRadius: 4, backgroundColor: cores.borda, overflow: 'hidden' }}>
      <View style={{ width: `${fracao * 100}%`, height: '100%', backgroundColor: cores.primaria }} />
    </View>
  );
}

function Pessoa({ nome }: { nome: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
      <Avatar nome={nome} />
      <Texto style={{ flex: 1 }}>{nome}</Texto>
    </View>
  );
}

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

  const marcaram = dados ? dados.membros - dados.faltantes.length : 0;

  return (
    <Tela aoAtualizar={() => consulta.refetch()}>
      <Cartao style={{ gap: 12 }}>
        {dados && dados.equipes.length > 1 && (
          <LinhaDeFiltro
            titulo="Equipe"
            opcoes={dados.equipes.map((e) => ({ valor: String(e.id), rotulo: e.nome }))}
            valor={String(dados.equipe_id)}
            aoEscolher={(valor) => setEquipe(Number(valor))}
          />
        )}
        <LinhaDeFiltro titulo="Mês" opcoes={MESES} valor={mes} aoEscolher={setMes} />
      </Cartao>

      <Estado consulta={consulta} />
      {dados && (
        <>
          <Cartao style={{ gap: 12 }}>
            <View style={{ gap: 4 }}>
              <Subtitulo>
                {dados.faltantes.length === 0
                  ? 'Todos já marcaram 🙌'
                  : dados.faltantes.length === 1
                    ? '1 pessoa ainda não marcou'
                    : `${dados.faltantes.length} pessoas ainda não marcaram`}
              </Subtitulo>
              <Suave>
                {marcaram} de {dados.membros} já marcaram disponibilidade em {nomeDoMes}
              </Suave>
            </View>
            <Progresso feito={marcaram} total={dados.membros} />
            {dados.faltantes.length > 0 && (
              <View style={{ gap: 10 }}>
                <Rotulo>Faltam marcar</Rotulo>
                {dados.faltantes.map((pessoa) => (
                  <Pessoa key={pessoa.id} nome={pessoa.nome} />
                ))}
              </View>
            )}
          </Cartao>

          <Erro erro={pedir.error} />
          {dados.faltantes.length > 0 && (
            <View style={{ gap: 8 }}>
              <Suave>Só quem ainda não marcou nada em {nomeDoMes} recebe o pedido.</Suave>
              <Botao
                titulo="Pedir pelo app"
                carregando={pedir.isPending && pedir.variables?.canal === 'app'}
                aoTocar={() => enviar('app')}
              />
              <Botao
                titulo="Pedir pelo app e por e-mail"
                variante="secundario"
                carregando={pedir.isPending && pedir.variables?.canal === 'todos'}
                aoTocar={() => enviar('todos')}
              />
            </View>
          )}
        </>
      )}
    </Tela>
  );
}
