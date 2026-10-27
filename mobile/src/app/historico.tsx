import { router } from 'expo-router';
import { Text, View } from 'react-native';

import { diaCurto, mesEAno } from '../lib/datas';
import { useHistorico } from '../lib/hooks';
import { useTema } from '../lib/tema';
import { Cartao, Estado, Linha, Suave, Subtitulo, Tela } from '../lib/ui';

/** Quantas escalas mostrar em "Últimas escalas" (o servidor também manda só 10). */
const ULTIMAS = 10;

function Numero({ valor, rotulo }: { valor: number; rotulo: string }) {
  const { cores } = useTema();
  return (
    <Cartao style={{ flex: 1, alignItems: 'center', gap: 2 }}>
      <Text style={{ color: cores.primaria, fontSize: 28, fontWeight: '700' }}>{valor}</Text>
      <Suave>{rotulo}</Suave>
    </Cartao>
  );
}

/** Quantas vezes o voluntário já serviu, em quais funções, e as últimas escalas. */
export default function MeuHistorico() {
  const consulta = useHistorico();
  const dados = consulta.data;

  return (
    <Tela aoAtualizar={() => consulta.refetch()}>
      <Estado
        consulta={consulta}
        vazio={dados?.total === 0 && 'Você ainda não serviu em nenhum culto. Quando servir, ele aparece aqui. 💚'}
      />
      {!!dados?.total && (
        <>
          <View style={{ flexDirection: 'row', gap: 12 }}>
            <Numero valor={dados.mes} rotulo="este mês" />
            <Numero valor={dados.ano} rotulo="este ano" />
            <Numero valor={dados.total} rotulo="no total" />
          </View>
          {dados.desde && <Suave style={{ textAlign: 'center' }}>Servindo desde {mesEAno(dados.desde)}</Suave>}

          <Subtitulo style={{ marginTop: 8 }}>Por função</Subtitulo>
          {dados.por_funcao.map((f) => (
            <Linha
              key={`${f.equipe}-${f.funcao}`}
              titulo={f.funcao}
              detalhe={f.equipe}
              status={f.total === 1 ? '1 vez' : `${f.total} vezes`}
            />
          ))}

          <Subtitulo style={{ marginTop: 8 }}>Últimas escalas</Subtitulo>
          {dados.ultimas.slice(0, ULTIMAS).map((escala) => (
            <Linha
              key={escala.id}
              titulo={escala.evento.nome}
              detalhe={`${diaCurto(escala.evento.data_inicio)} · ${escala.funcao}`}
              aoTocar={() => router.push({ pathname: '/escala/[id]', params: { id: escala.id } })}
            />
          ))}
        </>
      )}
    </Tela>
  );
}
