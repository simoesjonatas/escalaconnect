import { eachDayOfInterval, endOfMonth, format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, View } from 'react-native';

import { CampoDeDataHora, juntar } from '../../../lib/data-hora';
import { alternar, ChipsDeEscolha, FuncoesDaEquipe, Passo } from '../../../lib/formulario-lider';
import { useGerarEventosEmMassa, useOpcoesDeEventos } from '../../../lib/hooks';
import { OpcoesDeEventos } from '../../../lib/types';
import { Botao, Campo, Cartao, Erro, Estado, Subtitulo, Suave, Tela } from '../../../lib/ui';

// Mesma ordem e valores do site (date.weekday do Python): 0 = segunda ... 6 = domingo.
const DIAS = [
  { valor: 0, rotulo: 'Segunda' },
  { valor: 1, rotulo: 'Terça' },
  { valor: 2, rotulo: 'Quarta' },
  { valor: 3, rotulo: 'Quinta' },
  { valor: 4, rotulo: 'Sexta' },
  { valor: 5, rotulo: 'Sábado' },
  { valor: 6, rotulo: 'Domingo' },
];
const diaPython = (d: Date) => (d.getDay() + 6) % 7;
const AMBOS = 'ambos';

const hora = (h: number, m = 0) => {
  const d = new Date();
  d.setHours(h, m, 0, 0);
  return d;
};

/** "Período" do site: mês atual, próximo mês ou os dois. */
function periodos(meses: OpcoesDeEventos['meses']) {
  const [atual, proximo] = meses;
  return [
    { valor: atual.valor, rotulo: `Mês atual — ${atual.rotulo}` },
    { valor: proximo.valor, rotulo: `Próximo mês — ${proximo.rotulo}` },
    { valor: AMBOS, rotulo: 'Mês atual e próximo mês' },
  ];
}

/** Mesmas regras do servidor: dias escolhidos do(s) mês(es), sem as datas que já passaram. */
function datasPrevistas(meses: string[], dias: number[], inicio: Date) {
  const agora = new Date();
  return meses.flatMap((mes) => {
    const primeiro = new Date(`${mes}-01T12:00:00`);
    return eachDayOfInterval({ start: primeiro, end: endOfMonth(primeiro) })
      .filter((d) => dias.includes(diaPython(d)))
      .map((d) => juntar(d, inicio))
      .filter((d) => d > agora);
  });
}

/** Mesmo "Gerar em Massa" do site: 1 Evento, 2 Funções de cada evento, 3 Quando (sem a observação, que ninguém usa). */
export default function EventosEmMassa() {
  const opcoes = useOpcoesDeEventos();
  const gerar = useGerarEventosEmMassa();
  const [nome, setNome] = useState('');
  const [equipe, setEquipe] = useState<number>();
  const [funcoes, setFuncoes] = useState<number[]>([]);
  const [periodo, setPeriodo] = useState<string>();
  const [dias, setDias] = useState<number[]>([]);
  const [inicio, setInicio] = useState(hora(19, 30));
  const [fim, setFim] = useState(hora(21, 30));

  const dados = opcoes.data;
  const equipeId = equipe ?? dados?.equipes[0]?.id;
  const equipeEscolhida = dados?.equipes.find((e) => e.id === equipeId);
  const periodoEscolhido = periodo ?? dados?.meses[0]?.valor;
  const meses = !dados ? [] : periodoEscolhido === AMBOS ? dados.meses.map((m) => m.valor) : [periodoEscolhido!];
  const datas = dias.length ? datasPrevistas(meses, dias, inicio) : null;
  const horarioInvalido = juntar(new Date(), fim) <= juntar(new Date(), inicio);
  const n = funcoes.length;

  function gerarEventos() {
    if (!equipeId) return;
    gerar.mutate(
      {
        nome: nome.trim(),
        equipe_id: equipeId,
        meses,
        dias_da_semana: dias,
        horario_inicio: format(inicio, 'HH:mm'),
        horario_fim: format(fim, 'HH:mm'),
        observacao: '',
        funcao_ids: funcoes,
      },
      {
        onSuccess: ({ criados, ignorados, vagas_por_evento }) => {
          const vagas = vagas_por_evento && criados ? ` com ${vagas_por_evento} vaga(s) cada` : '';
          Alert.alert(
            'Pronto',
            `${criados} evento(s) criado(s)${vagas}. ${ignorados} data(s) passada(s) ou já existente(s) ignorada(s).`,
          );
          router.back();
        },
      },
    );
  }

  return (
    <Tela>
      <Estado consulta={opcoes} vazio={dados?.equipes.length === 0 && 'Você não lidera nenhuma equipe.'} />
      {dados && dados.equipes.length > 0 && (
        <>
          <Passo numero={1} titulo="Evento">
            <Campo rotulo="Nome do evento" value={nome} onChangeText={setNome} />
            {dados.equipes.length > 1 ? (
              <ChipsDeEscolha
                titulo="Equipe"
                opcoes={dados.equipes.map((e) => ({ valor: e.id, rotulo: e.nome }))}
                ativas={equipeId ? [equipeId] : []}
                aoTocar={(id) => {
                  setEquipe(id);
                  setFuncoes([]);
                }}
              />
            ) : (
              <Suave>Equipe: {dados.equipes[0].nome}</Suave>
            )}
          </Passo>

          <Passo
            numero={2}
            titulo="Funções de cada evento"
            dica="Cada função marcada vira uma vaga em todos os eventos gerados. Pode deixar sem nenhuma e adicionar depois.">
            <FuncoesDaEquipe equipe={equipeEscolhida} funcoes={funcoes} aoMudar={setFuncoes} />
          </Passo>

          <Passo numero={3} titulo="Quando">
            <ChipsDeEscolha
              titulo="Período"
              opcoes={periodos(dados.meses)}
              ativas={periodoEscolhido ? [periodoEscolhido] : []}
              aoTocar={setPeriodo}
            />
            <ChipsDeEscolha titulo="Dias da semana" opcoes={DIAS} ativas={dias} aoTocar={(d) => setDias(alternar(dias, d))} />
            <CampoDeDataHora rotulo="Horário de início" modo="time" valor={inicio} aoMudar={setInicio} />
            <CampoDeDataHora rotulo="Horário de término" modo="time" valor={fim} aoMudar={setFim} />
            {horarioInvalido && <Suave>O horário de término deve ser posterior ao início.</Suave>}
          </Passo>

          {datas && (
            <Cartao style={{ gap: 6 }}>
              <Subtitulo>
                {datas.length === 0
                  ? 'Nenhuma data futura com essas escolhas.'
                  : `Serão criados ${datas.length} evento${datas.length === 1 ? '' : 's'}` +
                    (n ? `, cada um com ${n} vaga${n === 1 ? '' : 's'} (${datas.length * n} no total)` : ', sem vagas') +
                    '.'}
              </Subtitulo>
              {datas.length > 0 && (
                <View>
                  <Suave>{datas.map((d) => format(d, 'EEE d/MMM', { locale: ptBR })).join(' · ')}</Suave>
                </View>
              )}
            </Cartao>
          )}

          <Erro erro={gerar.error} />
          <Botao
            titulo="Gerar eventos"
            desabilitado={!nome.trim() || !datas?.length || horarioInvalido}
            carregando={gerar.isPending}
            aoTocar={gerarEventos}
          />
        </>
      )}
    </Tela>
  );
}
