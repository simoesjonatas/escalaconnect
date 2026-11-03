import { addDays, addHours } from 'date-fns';
import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, View } from 'react-native';

import { CampoDeDataHora, juntar } from '../../../lib/data-hora';
import { ChipsDeEscolha } from '../../../lib/formulario-lider';
import { useCriarEvento, useOpcoesDeEventos } from '../../../lib/hooks';
import { Botao, Campo, Cartao, Erro, Estado, Rotulo, Suave, Tela } from '../../../lib/ui';

/** Amanhã no horário dado (o padrão é 19:30, horário comum de culto/ensaio). */
function amanhaAs(h: number, m: number) {
  const d = addDays(new Date(), 1);
  d.setHours(h, m, 0, 0);
  return d;
}

const PUBLICO = 0;

/** Mesmo "Criar Evento" do site: nome, início, fim e equipe (a observação ficou só no site, ninguém usa). */
export default function NovoEvento() {
  const opcoes = useOpcoesDeEventos();
  const criar = useCriarEvento();
  const [nome, setNome] = useState('');
  const [inicio, setInicio] = useState(amanhaAs(19, 30));
  const [fim, setFim] = useState(addHours(amanhaAs(19, 30), 2));
  const [equipe, setEquipe] = useState<number>();

  const dados = opcoes.data;
  const equipeId = equipe ?? dados?.equipes[0]?.id ?? (dados?.admin ? PUBLICO : undefined);
  const fimInvalido = fim <= inicio;

  // Mudar o início leva o fim junto, mantendo a duração (como quem ajusta o horário no site).
  function mudarInicio(novo: Date) {
    setFim(new Date(fim.getTime() + (novo.getTime() - inicio.getTime())));
    setInicio(novo);
  }

  function salvar() {
    if (equipeId === undefined) return;
    criar.mutate(
      {
        nome: nome.trim(),
        // Evento público (sem equipe) só o admin cria, como no site.
        equipe_id: equipeId === PUBLICO ? null : equipeId,
        data_inicio: inicio.toISOString(),
        data_fim: fim.toISOString(),
        observacao: '',
        funcao_ids: [],
      },
      {
        onSuccess: (evento) => {
          Alert.alert('Evento criado', `${evento.nome} foi criado. Para pôr as funções, use "Funções em eventos".`);
          router.back();
        },
      },
    );
  }

  const opcoesDeEquipe = [
    ...(dados?.equipes ?? []).map((e) => ({ valor: e.id, rotulo: e.nome })),
    ...(dados?.admin ? [{ valor: PUBLICO, rotulo: 'Público (todos podem ver)' }] : []),
  ];

  return (
    <Tela>
      <Estado consulta={opcoes} vazio={dados?.equipes.length === 0 && !dados?.admin && 'Você não lidera nenhuma equipe.'} />
      {dados && opcoesDeEquipe.length > 0 && (
        <>
          <Cartao style={{ gap: 14 }}>
            <Campo rotulo="Nome" value={nome} onChangeText={setNome} placeholder="Ex.: Ensaio do louvor" />
            <View style={{ gap: 8 }}>
              <Rotulo>Data de início</Rotulo>
              <CampoDeDataHora rotulo="Dia" modo="date" valor={inicio} minimo={new Date()} aoMudar={(d) => mudarInicio(juntar(d, inicio))} />
              <CampoDeDataHora rotulo="Hora" modo="time" valor={inicio} aoMudar={(h) => mudarInicio(juntar(inicio, h))} />
            </View>
            <View style={{ gap: 8 }}>
              <Rotulo>Data de fim</Rotulo>
              <CampoDeDataHora rotulo="Dia" modo="date" valor={fim} minimo={inicio} aoMudar={(d) => setFim(juntar(d, fim))} />
              <CampoDeDataHora rotulo="Hora" modo="time" valor={fim} aoMudar={(h) => setFim(juntar(fim, h))} />
              {fimInvalido && <Suave>A data de fim precisa ser depois do início.</Suave>}
            </View>
            {opcoesDeEquipe.length > 1 ? (
              <ChipsDeEscolha
                titulo="Equipe"
                opcoes={opcoesDeEquipe}
                ativas={equipeId === undefined ? [] : [equipeId]}
                aoTocar={setEquipe}
              />
            ) : (
              <Suave>Equipe: {opcoesDeEquipe[0].rotulo}</Suave>
            )}
          </Cartao>
          <Erro erro={criar.error} />
          <Botao
            titulo="Criar evento"
            desabilitado={!nome.trim() || fimInvalido}
            carregando={criar.isPending}
            aoTocar={salvar}
          />
        </>
      )}
    </Tela>
  );
}
