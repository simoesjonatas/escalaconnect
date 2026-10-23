import { router } from 'expo-router';
import { ReactNode, useState } from 'react';
import { Alert, Pressable, View } from 'react-native';

import { periodo } from '../../lib/datas';
import { AcaoDoLider, useAcaoDoLider, usePendenciasDoLider, useVagas } from '../../lib/hooks';
import { useTema } from '../../lib/tema';
import { EscalaDaEquipe, Vaga } from '../../lib/types';
import { Botao, Cartao, Erro, Estado, Etiqueta, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

const VAGAS_VISIVEIS = 8;

const abrirVaga = (id: number) => router.push({ pathname: '/lider/vaga/[id]', params: { id } });

/** Pendências das equipes que o usuário lidera (aprovar/recusar) e vagas em aberto. */
export default function Lideranca() {
  const pendencias = usePendenciasDoLider();
  const vagas = useVagas();
  const acao = useAcaoDoLider();
  const [todasAsVagas, setTodasAsVagas] = useState(false);
  const { cores } = useTema();

  const dados = pendencias.data;
  const semPendencias = dados && !dados.impedimentos.length && !dados.trocas.length && !dados.candidaturas.length;

  function executar(pedido: AcaoDoLider, titulo: string, mensagem: string) {
    const aprovar = pedido.acao === 'aprovar';
    Alert.alert(titulo, mensagem, [
      { text: 'Voltar', style: 'cancel' },
      {
        text: aprovar ? 'Aprovar' : 'Recusar',
        style: aprovar ? 'default' : 'destructive',
        onPress: () =>
          acao.mutate(pedido, {
            onSuccess: (resposta) => {
              if (!resposta?.vaga_id) return;
              const vagaId = resposta.vaga_id;
              Alert.alert('Vaga liberada', 'Quer escalar outra pessoa agora?', [
                { text: 'Depois', style: 'cancel' },
                { text: 'Escalar', onPress: () => abrirVaga(vagaId) },
              ]);
            },
          }),
      },
    ]);
  }

  /** Botões Recusar/Aprovar de uma pendência, com confirmação. */
  const decisao = (pedido: Omit<AcaoDoLider, 'acao'>, aprovar: string, recusar: string) => {
    const emAndamento = acao.isPending && acao.variables?.tipo === pedido.tipo && acao.variables.id === pedido.id;
    return (
      <Decisao
        bloqueado={acao.isPending}
        carregando={emAndamento ? (acao.variables?.acao ?? null) : null}
        aoDecidir={(qual) =>
          executar({ ...pedido, acao: qual }, qual === 'aprovar' ? 'Aprovar' : 'Recusar', qual === 'aprovar' ? aprovar : recusar)
        }
      />
    );
  };

  return (
    <Tela
      atualizando={pendencias.isRefetching || vagas.isRefetching}
      aoAtualizar={() => {
        void pendencias.refetch();
        void vagas.refetch();
      }}>
      <Estado consulta={pendencias} />
      <Erro erro={acao.error} />

      {semPendencias && (
        <Cartao>
          <Subtitulo>Tudo em dia 🙌</Subtitulo>
          <Suave>Nenhum impedimento, troca ou candidatura esperando você.</Suave>
        </Cartao>
      )}

      {!!dados?.impedimentos.length && (
        <Secao titulo="Impedimentos" total={dados.impedimentos.length}>
          {dados.impedimentos.map((item) => (
            <Cartao key={item.id}>
              <Etiqueta texto="Impedimento" cor={cores.perigo} />
              <Subtitulo>{item.pessoa.nome}</Subtitulo>
              <ResumoDaEscala escala={item.escala} />
              <Texto>Motivo: {item.motivo}</Texto>
              {decisao(
                { tipo: 'impedimentos', id: item.id },
                `${item.pessoa.nome} sai da escala e a vaga fica aberta.`,
                `${item.pessoa.nome} continua escalado e será avisado.`,
              )}
            </Cartao>
          ))}
        </Secao>
      )}

      {!!dados?.trocas.length && (
        <Secao titulo="Pedidos de troca" total={dados.trocas.length}>
          {dados.trocas.map((item) => (
            <Cartao key={item.id}>
              <Etiqueta texto="Troca" cor={cores.neutra} />
              <Subtitulo>{item.pessoa.nome}</Subtitulo>
              <ResumoDaEscala escala={item.escala} />
              {decisao(
                { tipo: 'trocas', id: item.id },
                `${item.pessoa.nome} sai da escala e a vaga fica aberta.`,
                `${item.pessoa.nome} continua escalado e será avisado.`,
              )}
            </Cartao>
          ))}
        </Secao>
      )}

      {!!dados?.candidaturas.length && (
        <Secao titulo="Candidaturas" total={dados.candidaturas.length}>
          {dados.candidaturas.map((item) => (
            <Cartao key={item.id}>
              <Subtitulo>{item.pessoa.nome}</Subtitulo>
              <Suave>Quer entrar na equipe {item.equipe}</Suave>
              {decisao(
                { tipo: 'candidaturas', id: item.id },
                `${item.pessoa.nome} passa a fazer parte da equipe ${item.equipe}.`,
                `O pedido de ${item.pessoa.nome} para a equipe ${item.equipe} será descartado.`,
              )}
            </Cartao>
          ))}
        </Secao>
      )}

      <Secao titulo="Vagas em aberto" total={vagas.data?.length}>
        <Estado consulta={vagas} vazio={vagas.data?.length === 0 && 'Nenhuma vaga em aberto nos próximos 60 dias.'} />
        {(todasAsVagas ? vagas.data : vagas.data?.slice(0, VAGAS_VISIVEIS))?.map((vaga) => (
          <CartaoDeVaga key={vaga.id} vaga={vaga} />
        ))}
        {!todasAsVagas && (vagas.data?.length ?? 0) > VAGAS_VISIVEIS && (
          <Botao
            titulo={`Ver todas (${vagas.data?.length})`}
            variante="secundario"
            aoTocar={() => setTodasAsVagas(true)}
          />
        )}
      </Secao>
    </Tela>
  );
}

function Decisao({
  bloqueado,
  carregando,
  aoDecidir,
}: {
  bloqueado: boolean;
  carregando: AcaoDoLider['acao'] | null;
  aoDecidir: (acao: AcaoDoLider['acao']) => void;
}) {
  return (
    <View style={{ flexDirection: 'row', gap: 8 }}>
      <View style={{ flex: 1 }}>
        <Botao
          titulo="Recusar"
          variante="secundario"
          carregando={carregando === 'recusar'}
          desabilitado={bloqueado}
          aoTocar={() => aoDecidir('recusar')}
        />
      </View>
      <View style={{ flex: 1 }}>
        <Botao
          titulo="Aprovar"
          carregando={carregando === 'aprovar'}
          desabilitado={bloqueado}
          aoTocar={() => aoDecidir('aprovar')}
        />
      </View>
    </View>
  );
}

function Secao({ titulo, total, children }: { titulo: string; total?: number; children: ReactNode }) {
  return (
    <View style={{ gap: 12 }}>
      <Subtitulo style={{ marginTop: 8 }}>
        {titulo}
        {total ? ` (${total})` : ''}
      </Subtitulo>
      {children}
    </View>
  );
}

function ResumoDaEscala({ escala }: { escala: EscalaDaEquipe }) {
  return (
    <>
      <Texto>
        {escala.evento.nome} · {periodo(escala.evento.data_inicio, escala.evento.data_fim)}
      </Texto>
      <Suave>
        {escala.funcao} · {escala.equipe}
      </Suave>
    </>
  );
}

function CartaoDeVaga({ vaga }: { vaga: Vaga }) {
  const { cores } = useTema();
  return (
    <Pressable onPress={() => abrirVaga(vaga.id)} accessibilityRole="button">
      <Cartao>
        <Subtitulo>{vaga.evento.nome}</Subtitulo>
        <Texto>{periodo(vaga.evento.data_inicio, vaga.evento.data_fim)}</Texto>
        <Suave>
          {vaga.funcao} · {vaga.equipe}
        </Suave>
        <Texto style={{ color: vaga.disponiveis ? cores.confirmada : cores.pendente, fontWeight: '600' }}>
          {vaga.disponiveis === 0
            ? 'Ninguém marcou disponibilidade · tocar para escalar'
            : `${vaga.disponiveis} ${vaga.disponiveis === 1 ? 'disponível' : 'disponíveis'} · tocar para escalar`}
        </Texto>
      </Cartao>
    </Pressable>
  );
}
