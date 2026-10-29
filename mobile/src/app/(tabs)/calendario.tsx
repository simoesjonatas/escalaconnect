import Ionicons from '@expo/vector-icons/Ionicons';
import { endOfMonth, format, startOfMonth } from 'date-fns';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Alert, Pressable, Text, View } from 'react-native';
import { Calendar, LocaleConfig } from 'react-native-calendars';

import { useAuth } from '../../lib/auth';
import { chaveDoDia, diaPorExtenso, hora } from '../../lib/datas';
import { aplicar, CartaoDeFiltros, escolher, Filtro, TODOS } from '../../lib/filtros';
import { useCultos, useEscalas, useEventos, useOferta, useVagas, useVagasAbertas } from '../../lib/hooks';
import { Cores, useTema } from '../../lib/tema';
import { Culto, EventoCalendario, Vaga, VagaAberta } from '../../lib/types';
import { Botao, Cartao, Erro, Estado, Etiqueta, Rotulo, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

LocaleConfig.locales['pt-br'] = {
  monthNames: [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
  ],
  monthNamesShort: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'],
  dayNames: ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'],
  dayNamesShort: ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'],
  today: 'Hoje',
};
LocaleConfig.defaultLocale = 'pt-br';

// Mesmas cores do calendário do site: verde confirmada, laranja a confirmar, azul sem escala.
const corDoEvento = (e: EventoCalendario, cores: Cores) =>
  e.escalado ? (e.confirmada ? cores.confirmada : cores.pendente) : cores.neutra;

/** Agrupa uma lista pelo id do evento. */
function porEvento<T>(itens: T[] | undefined, evento: (item: T) => number) {
  const mapa = new Map<number, T[]>();
  for (const item of itens ?? []) mapa.set(evento(item), [...(mapa.get(evento(item)) ?? []), item]);
  return mapa;
}

const plural = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`;

export default function Calendario() {
  const [mes, setMes] = useState(() => startOfMonth(new Date()));
  const [dia, setDia] = useState(() => chaveDoDia(new Date()));
  const [situacao, setSituacao] = useState(TODOS);
  const [tipo, setTipo] = useState(TODOS);
  const eventos = useEventos(format(mes, 'yyyy-MM-dd'), format(endOfMonth(mes), 'yyyy-MM-dd'));
  const escalas = useEscalas();
  const lider = useAuth().usuario?.lider ?? false;
  // Voluntário: vagas em que pode se oferecer. Líder: cultos e vagas das equipes que lidera.
  const vagasAbertas = useVagasAbertas();
  const cultos = useCultos(lider);
  const vagasDoLider = useVagas(lider);
  const oferta = useOferta();
  const { cores, escuro } = useTema();

  const minhasVagas = useMemo(() => porEvento(vagasAbertas.data, (v) => v.evento.id), [vagasAbertas.data]);
  const vagasDaEquipe = useMemo(() => porEvento(vagasDoLider.data, (v) => v.evento.id), [vagasDoLider.data]);
  const cultoDoLider = useMemo(() => new Map((cultos.data ?? []).map((c) => [c.id, c])), [cultos.data]);

  // Filtros sobre os eventos do mês: valem para os pontos do calendário e para a lista do dia.
  const todos = eventos.data ?? [];
  const situacoes: Filtro<EventoCalendario>[] = [
    { valor: 'sirvo', rotulo: 'Onde sirvo', aplica: (e) => e.escalado },
    { valor: 'vagas', rotulo: 'Com vaga para mim', aplica: (e) => minhasVagas.has(e.id) },
    ...(lider
      ? [{ valor: 'equipe', rotulo: 'Vagas da minha equipe', aplica: (e: EventoCalendario) => vagasDaEquipe.has(e.id) }]
      : []),
  ];
  const porSituacao = escolher(situacoes, todos, situacao);
  const daSituacao = aplicar(todos, porSituacao.ativo);
  const tipos: Filtro<EventoCalendario>[] = [
    { valor: 'gerais', rotulo: 'Cultos', aplica: (e) => !e.equipe_id },
    ...[...new Map(todos.filter((e) => e.equipe_id).map((e) => [e.equipe_id, e.equipe ?? ''])).entries()]
      .sort(([, a], [, b]) => a.localeCompare(b))
      .map(([id, nome]) => ({ valor: String(id), rotulo: nome, aplica: (e: EventoCalendario) => e.equipe_id === id })),
  ];
  const porTipo = escolher(tipos, daSituacao, tipo);
  const visiveis = aplicar(daSituacao, porTipo.ativo);

  const porDia = useMemo(() => {
    const mapa: Record<string, EventoCalendario[]> = {};
    for (const evento of visiveis) (mapa[chaveDoDia(evento.data_inicio)] ??= []).push(evento);
    return mapa;
  }, [visiveis]);

  const marcacoes = useMemo(() => {
    const marcas: Record<string, object> = {};
    for (const [chave, doDia] of Object.entries(porDia)) {
      // Um ponto por cor presente no dia.
      const dots = [...new Set(doDia.map((e) => corDoEvento(e, cores)))].map((color) => ({ key: color, color }));
      marcas[chave] = { dots };
    }
    marcas[dia] = { ...marcas[dia], selected: true, selectedColor: cores.primaria };
    return marcas;
  }, [porDia, dia, cores]);

  function abrir(evento: EventoCalendario) {
    // Evento em que estou escalado abre a minha escala; para o líder, o culto da equipe.
    const escala = escalas.data?.find((e) => e.evento.id === evento.id);
    if (escala) router.push({ pathname: '/escala/[id]', params: { id: escala.id } });
    else if (cultoDoLider.has(evento.id)) router.push({ pathname: '/lider/culto/[id]', params: { id: evento.id } });
  }

  function oferecer(vaga: VagaAberta) {
    Alert.alert('Quero servir', `A liderança da equipe ${vaga.equipe} vai receber sua oferta para ${vaga.funcao}.`, [
      { text: 'Voltar', style: 'cancel' },
      { text: 'Me oferecer', onPress: () => oferta.mutate({ vagaId: vaga.id }) },
    ]);
  }

  function limparFiltros() {
    setSituacao(TODOS);
    setTipo(TODOS);
  }

  const doDia = porDia[dia] ?? [];
  return (
    <Tela
      aoAtualizar={() =>
        Promise.all([
          eventos.refetch(),
          vagasAbertas.refetch(),
          ...(lider ? [cultos.refetch(), vagasDoLider.refetch()] : []),
        ])
      }>
      <CartaoDeFiltros
        titulo="Filtrar eventos"
        nome="eventos no mês"
        linhas={[
          { titulo: 'Mostrar', todos: 'Todos', escolha: porSituacao, aoEscolher: setSituacao },
          { titulo: 'Tipo', todos: 'Todos', escolha: porTipo, aoEscolher: setTipo },
        ]}
        total={todos.length}
        mostrando={visiveis.length}
        aoLimpar={limparFiltros}
      />
      <Calendar
        markingType="multi-dot"
        markedDates={marcacoes}
        onDayPress={(d) => setDia(d.dateString)}
        onMonthChange={(m) => setMes(new Date(m.year, m.month - 1, 1))}
        key={escuro ? 'escuro' : 'claro'} // o calendário não reaplica o tema sem remontar
        theme={{
          calendarBackground: cores.cartao,
          dayTextColor: cores.texto,
          monthTextColor: cores.texto,
          textSectionTitleColor: cores.textoSuave,
          textDisabledColor: cores.borda,
          todayTextColor: cores.primaria,
          arrowColor: cores.primaria,
          selectedDayTextColor: cores.sobrePrimaria,
        }}
        style={{ borderRadius: 12, borderWidth: 1, borderColor: cores.borda }}
      />
      <Subtitulo>{diaPorExtenso(`${dia}T12:00:00`)}</Subtitulo>
      <Erro erro={oferta.error} />
      <Estado consulta={eventos} vazio={doDia.length === 0 && 'Nenhum evento neste dia.'} />
      {doDia.map((evento) => {
        const culto = cultoDoLider.get(evento.id);
        return (
          <Pressable key={evento.id} onPress={() => abrir(evento)} disabled={!evento.escalado && !culto}>
            <Cartao>
              {evento.escalado && (
                <Etiqueta texto={evento.confirmada ? 'Confirmada' : 'A confirmar'} cor={corDoEvento(evento, cores)} />
              )}
              <Subtitulo>{evento.nome}</Subtitulo>
              <Texto>
                {hora(evento.data_inicio)} – {hora(evento.data_fim)}
              </Texto>
              {evento.escalado && <Suave>Você serve como: {evento.funcoes.join(', ')}</Suave>}
              {!!evento.equipe && <Suave>Evento da equipe {evento.equipe}</Suave>}

              {culto && <ResumoDoLider culto={culto} vagas={vagasDaEquipe.get(evento.id) ?? []} />}

              {(minhasVagas.get(evento.id) ?? []).map((vaga) => (
                <VagaParaMim
                  key={vaga.id}
                  vaga={vaga}
                  ocupada={oferta.isPending && oferta.variables?.vagaId === vaga.id}
                  aoOferecer={() => oferecer(vaga)}
                  aoDesistir={() => oferta.mutate({ vagaId: vaga.id, desistir: true })}
                />
              ))}
            </Cartao>
          </Pressable>
        );
      })}
    </Tela>
  );
}

/** Prévia para o líder: vagas das equipes dele, quem quer servir, quem está disponível e quem falta confirmar. */
function ResumoDoLider({ culto, vagas }: { culto: Culto; vagas: Vaga[] }) {
  const { cores } = useTema();
  const ofertas = vagas.reduce((soma, v) => soma + (v.ofertas ?? 0), 0);
  const comDisponiveis = vagas.filter((v) => v.disponiveis > 0).length;
  const linhas = [
    culto.vagas ? { icone: 'alert-circle-outline' as const, texto: plural(culto.vagas, 'vaga em aberto', 'vagas em aberto'), cor: cores.pendente } : null,
    ofertas ? { icone: 'hand-left-outline' as const, texto: `${plural(ofertas, 'pessoa quer', 'pessoas querem')} servir`, cor: cores.confirmada } : null,
    comDisponiveis ? { icone: 'checkmark-circle-outline' as const, texto: `${plural(comDisponiveis, 'vaga tem', 'vagas têm')} gente disponível`, cor: cores.confirmada } : null,
    culto.pendentes ? { icone: 'time-outline' as const, texto: plural(culto.pendentes, 'escalado falta confirmar', 'escalados faltam confirmar'), cor: cores.textoSuave } : null,
  ].filter((l) => l !== null);
  return (
    <View style={{ gap: 6, marginTop: 6, paddingTop: 10, borderTopWidth: 1, borderTopColor: cores.borda }}>
      <Rotulo>Sua equipe</Rotulo>
      {linhas.length === 0 ? (
        <Suave>Tudo preenchido e confirmado 🙌</Suave>
      ) : (
        linhas.map((l) => (
          <View key={l.texto} style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Ionicons name={l.icone} size={16} color={l.cor} />
            <Text style={{ color: l.cor, fontSize: 14, fontWeight: '600' }}>{l.texto}</Text>
          </View>
        ))
      )}
      <Botao
        titulo={culto.vagas ? 'Abrir o culto para escalar' : 'Abrir o culto'}
        variante="secundario"
        aoTocar={() => router.push({ pathname: '/lider/culto/[id]', params: { id: culto.id } })}
      />
    </View>
  );
}

/** Vaga em aberto da equipe do voluntário neste evento: oferecer-se ou desistir da oferta. */
function VagaParaMim({
  vaga,
  ocupada,
  aoOferecer,
  aoDesistir,
}: {
  vaga: VagaAberta;
  ocupada: boolean;
  aoOferecer: () => void;
  aoDesistir: () => void;
}) {
  const { cores } = useTema();
  return (
    <View style={{ gap: 6, marginTop: 6, paddingTop: 10, borderTopWidth: 1, borderTopColor: cores.borda }}>
      <Rotulo>Vaga em aberto · {vaga.equipe}</Rotulo>
      <Texto>{vaga.funcao}</Texto>
      {vaga.me_ofereci ? (
        <>
          <Suave>Você se ofereceu. A liderança vai decidir.</Suave>
          <Botao titulo="Desistir da oferta" variante="secundario" carregando={ocupada} aoTocar={aoDesistir} />
        </>
      ) : (
        <Botao titulo="Quero servir" carregando={ocupada} aoTocar={aoOferecer} />
      )}
    </View>
  );
}
