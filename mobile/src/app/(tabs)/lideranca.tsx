import Ionicons from '@expo/vector-icons/Ionicons';
import { router, useLocalSearchParams } from 'expo-router';
import { ComponentProps, useEffect, useState } from 'react';
import { Alert, Pressable, Text, View } from 'react-native';

import { diaCurto } from '../../lib/datas';
import { aplicar, CaixaDeFiltros, Chips, escolher, Filtro, filtrosDePeriodo, TODOS } from '../../lib/filtros';
import { AcaoDoLider, useAcaoDoLider, useCultos, usePendenciasDoLider, useVagas } from '../../lib/hooks';
import { Cores, useTema } from '../../lib/tema';
import { ContagemDoCulto, Culto, EscalaDaEquipe, PendenciasDoLider, Pessoa, Vaga } from '../../lib/types';
import { Botao, Cartao, Erro, Estado, Etiqueta, Linha, Segmentos, Suave, Subtitulo, Tela } from '../../lib/ui';

type Aba = 'pendencias' | 'cultos' | 'vagas';

const abrirVaga = (id: number) => router.push({ pathname: '/lider/vaga/[id]', params: { id } });

/** Uma pendência de qualquer tipo, já com os textos de cada lado da decisão. */
type Pendencia = {
  chave: string;
  pedido: Omit<AcaoDoLider, 'acao'>;
  tipo: { texto: string; cor: string };
  pessoa: Pessoa;
  equipe: { id: number; nome: string };
  escala?: EscalaDaEquipe;
  detalhe?: string;
  /** Atalho para decidir com mais contexto: a vaga (ofertas) ou o culto (impedimento e troca). */
  link?: { texto: string; abrir: () => void };
  aprovar: string;
  recusar: string;
};

const abrirCulto = (id: number) => router.push({ pathname: '/lider/culto/[id]', params: { id } });

/** Junta impedimentos, trocas e ofertas (por data do culto) e, por último, as candidaturas. */
function listarPendencias(dados: PendenciasDoLider, cores: Cores): Pendencia[] {
  const saida = (nome: string) => `${nome} sai da escala e a vaga fica aberta.`;
  const verCulto = (escala: EscalaDaEquipe) => ({ texto: 'Ver o culto', abrir: () => abrirCulto(escala.evento.id) });
  // Quantas ofertas cada vaga tem, para o atalho dizer quantas pessoas querem a mesma vaga.
  const ofertasPorVaga = new Map<number, number>();
  for (const o of dados.ofertas) ofertasPorVaga.set(o.escala.id, (ofertasPorVaga.get(o.escala.id) ?? 0) + 1);
  const continua = (nome: string) => `${nome} continua escalado e será avisado.`;
  const comData = [
    ...dados.impedimentos.map((i) => ({
      chave: `i${i.id}`,
      pedido: { tipo: 'impedimentos' as const, id: i.id },
      tipo: { texto: 'Impedimento', cor: cores.perigo },
      pessoa: i.pessoa,
      equipe: { id: i.escala.equipe_id, nome: i.escala.equipe },
      escala: i.escala,
      detalhe: `Motivo: ${i.motivo}`,
      link: verCulto(i.escala),
      aprovar: saida(i.pessoa.nome),
      recusar: continua(i.pessoa.nome),
    })),
    ...dados.trocas.map((t) => ({
      chave: `t${t.id}`,
      pedido: { tipo: 'trocas' as const, id: t.id },
      tipo: { texto: 'Troca', cor: cores.neutra },
      pessoa: t.pessoa,
      equipe: { id: t.escala.equipe_id, nome: t.escala.equipe },
      escala: t.escala,
      link: verCulto(t.escala),
      aprovar: saida(t.pessoa.nome),
      recusar: continua(t.pessoa.nome),
    })),
    ...dados.ofertas.map((o) => ({
      chave: `o${o.id}`,
      pedido: { tipo: 'ofertas' as const, id: o.id },
      tipo: { texto: 'Quer servir', cor: cores.confirmada },
      pessoa: o.pessoa,
      equipe: { id: o.escala.equipe_id, nome: o.escala.equipe },
      escala: o.escala,
      link: {
        texto:
          (ofertasPorVaga.get(o.escala.id) ?? 1) > 1
            ? `Ver os ${ofertasPorVaga.get(o.escala.id)} que querem esta vaga`
            : 'Ver a vaga e quem está disponível',
        abrir: () => abrirVaga(o.escala.id),
      },
      aprovar: `${o.pessoa.nome} fica com a vaga e recebe o aviso de escala.`,
      recusar: `A oferta de ${o.pessoa.nome} é descartada e a vaga continua aberta.`,
    })),
  ].sort((a, b) => a.escala.evento.data_inicio.localeCompare(b.escala.evento.data_inicio));
  const candidaturas: Pendencia[] = dados.candidaturas.map((c) => ({
    chave: `c${c.id}`,
    pedido: { tipo: 'candidaturas', id: c.id },
    tipo: { texto: 'Candidatura', cor: cores.pendente },
    pessoa: c.pessoa,
    equipe: { id: c.equipe_id, nome: c.equipe },
    detalhe: `Quer entrar na equipe ${c.equipe}`,
    aprovar: `${c.pessoa.nome} passa a fazer parte da equipe ${c.equipe}.`,
    recusar: `O pedido de ${c.pessoa.nome} para a equipe ${c.equipe} será descartado.`,
  }));
  return [...comData, ...candidaturas];
}

/** Uma opção por equipe que aparece na lista, em ordem alfabética. */
function filtrosDeEquipe<T>(equipes: [number, string][], daEquipe: (item: T, id: number) => boolean): Filtro<T>[] {
  return [...new Map(equipes)]
    .sort(([, a], [, b]) => a.localeCompare(b))
    .map(([id, nome]) => ({ valor: String(id), rotulo: nome, aplica: (item: T) => daEquipe(item, id) }));
}

const TIPOS_DE_PENDENCIA: Filtro<Pendencia>[] = (
  [
    ['impedimentos', 'Impedimentos'],
    ['trocas', 'Trocas'],
    ['ofertas', 'Quer servir'],
    ['candidaturas', 'Candidaturas'],
  ] as const
).map(([valor, rotulo]) => ({ valor, rotulo, aplica: (p: Pendencia) => p.pedido.tipo === valor }));

/** Pendências por tipo (impedimento, troca, oferta, candidatura) e, dentro dele, por equipe. */
function filtrarPendencias(pendencias: Pendencia[], equipe: string, tipo: string) {
  const porTipo = escolher(TIPOS_DE_PENDENCIA, pendencias, tipo);
  const doTipo = aplicar(pendencias, porTipo.ativo);
  const porEquipe = escolher(
    filtrosDeEquipe<Pendencia>(
      doTipo.map((p) => [p.equipe.id, p.equipe.nome]),
      (p, id) => p.equipe.id === id,
    ),
    doTipo,
    equipe,
    true,
  );
  return { porTipo, porEquipe, lista: aplicar(doTipo, porEquipe.ativo) };
}

/** Filtros dos cultos em sequência (equipe → período → situação): cada linha só oferece o que existe na anterior. */
function filtrarCultos(recebidos: Culto[], equipe: string, quando: string, situacao: string) {
  // Servidor anterior a esta versão não manda `por_equipe`: o filtro de equipe só não aparece.
  const cultos = recebidos.map((c) => ({ ...c, por_equipe: c.por_equipe ?? [] }));
  const porEquipe = escolher(
    filtrosDeEquipe<Culto>(
      cultos.flatMap((c) => c.por_equipe.map((e): [number, string] => [e.equipe_id, e.equipe])),
      (c, id) => c.por_equipe.some((e) => e.equipe_id === id),
    ),
    cultos,
    equipe,
    true,
  );
  // Com uma equipe escolhida, as contagens passam a ser só dela.
  const contagem = (c: Culto): ContagemDoCulto =>
    c.por_equipe.find((e) => String(e.equipe_id) === porEquipe.ativo?.valor) ?? c;
  const daEquipe = aplicar(cultos, porEquipe.ativo);
  const porPeriodo = escolher(filtrosDePeriodo<Culto>((c) => c.data_inicio), daEquipe, quando);
  const doPeriodo = aplicar(daEquipe, porPeriodo.ativo);
  const porSituacao = escolher<Culto>(
    [
      { valor: 'confirmar', rotulo: 'Falta confirmar', aplica: (c) => contagem(c).pendentes > 0 },
      { valor: 'vagas', rotulo: 'Com vagas', aplica: (c) => contagem(c).vagas > 0 },
      { valor: 'completos', rotulo: 'Tudo certo', aplica: (c) => !contagem(c).pendentes && !contagem(c).vagas },
    ],
    doPeriodo,
    situacao,
  );
  return { porEquipe, porPeriodo, porSituacao, contagem, lista: aplicar(doPeriodo, porSituacao.ativo) };
}

function filtrarVagas(vagas: Vaga[], equipe: string, quando: string, situacao: string) {
  const porEquipe = escolher(
    filtrosDeEquipe<Vaga>(
      vagas.map((v) => [v.equipe_id, v.equipe]),
      (v, id) => v.equipe_id === id,
    ),
    vagas,
    equipe,
    true,
  );
  const daEquipe = aplicar(vagas, porEquipe.ativo);
  const porPeriodo = escolher(filtrosDePeriodo<Vaga>((v) => v.evento.data_inicio), daEquipe, quando);
  const doPeriodo = aplicar(daEquipe, porPeriodo.ativo);
  const porSituacao = escolher<Vaga>(
    [
      { valor: 'ofertas', rotulo: 'Querem servir', aplica: (v) => (v.ofertas ?? 0) > 0 },
      { valor: 'disponiveis', rotulo: 'Com disponíveis', aplica: (v) => v.disponiveis > 0 },
      // Sem ninguém = nem oferta, nem disponibilidade: o líder precisa ir atrás de alguém.
      { valor: 'ninguem', rotulo: 'Sem ninguém', aplica: (v) => !v.ofertas && v.disponiveis === 0 },
    ],
    doPeriodo,
    situacao,
  );
  return { porEquipe, porPeriodo, porSituacao, lista: aplicar(doPeriodo, porSituacao.ativo) };
}

/** "2 querem servir · 1 disponível"; quem se ofereceu vem antes da disponibilidade marcada. */
function resumoDaVaga(vaga: Vaga) {
  const ofertas = vaga.ofertas ?? 0;
  const disponiveis = vaga.disponiveis
    ? `${vaga.disponiveis} ${vaga.disponiveis === 1 ? 'disponível' : 'disponíveis'}`
    : '';
  if (ofertas) {
    return [ofertas === 1 ? '1 quer servir' : `${ofertas} querem servir`, disponiveis].filter(Boolean).join(' · ');
  }
  return disponiveis || 'Ninguém marcou disponibilidade';
}

type Escolhas<T> = { uteis: Filtro<T>[]; ativo?: Filtro<T> };

/** Cartão de filtros de Cultos ou Vagas e a contagem logo abaixo ("Mostrando 3 de 12 cultos"). */
function FiltrosDoLider<T>({
  titulo,
  nome,
  linhas,
  total,
  mostrando,
  aoLimpar,
}: {
  titulo: string;
  nome: string;
  linhas: { titulo: string; todos: string; escolha: Escolhas<T>; aoEscolher: (valor: string) => void }[];
  total: number;
  mostrando: number;
  aoLimpar: () => void;
}) {
  if (total === 0) return null;
  const filtrando = linhas.some((l) => l.escolha.ativo);
  return (
    <>
      {linhas.some((l) => l.escolha.uteis.length > 0) && (
        <CaixaDeFiltros titulo={titulo} filtrando={filtrando} aoLimpar={aoLimpar}>
          {linhas.map((linha) => (
            <Chips key={linha.titulo} {...linha} />
          ))}
        </CaixaDeFiltros>
      )}
      <Suave>{filtrando ? `Mostrando ${mostrando} de ${total} ${nome}` : `${total} ${nome}`}</Suave>
    </>
  );
}

/** Painel do líder em três abas: pendências para decidir, próximos cultos e vagas em aberto. */
export default function Lideranca() {
  const pendencias = usePendenciasDoLider();
  const cultos = useCultos();
  const vagas = useVagas();
  const acao = useAcaoDoLider();
  const { cores } = useTema();
  const [escolhida, setEscolhida] = useState<Aba>();
  // Equipe e período valem para Cultos e Vagas; a situação é de cada aba.
  const [equipe, setEquipe] = useState(TODOS);
  const [quando, setQuando] = useState(TODOS);
  const [situacaoDoCulto, setSituacaoDoCulto] = useState(TODOS);
  const [situacaoDaVaga, setSituacaoDaVaga] = useState(TODOS);
  const [tipoDaPendencia, setTipoDaPendencia] = useState(TODOS);
  // Push e caixa de avisos abrem a aba já em Pendências (ver lib/push.ts).
  const { aba: abaDoLink, t } = useLocalSearchParams<{ aba?: Aba; t?: string }>();
  useEffect(() => {
    if (abaDoLink) setEscolhida(abaDoLink);
  }, [abaDoLink, t]);

  const lista = pendencias.data ? listarPendencias(pendencias.data, cores) : [];
  // Abre em Pendências quando há algo para decidir; senão, em Cultos.
  const aba: Aba = escolhida ?? (pendencias.data && lista.length === 0 ? 'cultos' : 'pendencias');
  const consulta = { pendencias, cultos, vagas }[aba];
  const daPendencia = filtrarPendencias(lista, equipe, tipoDaPendencia);
  const doCulto = filtrarCultos(cultos.data ?? [], equipe, quando, situacaoDoCulto);
  const daVaga = filtrarVagas(vagas.data ?? [], equipe, quando, situacaoDaVaga);
  function limparFiltros() {
    setEquipe(TODOS);
    setQuando(TODOS);
    setSituacaoDoCulto(TODOS);
    setSituacaoDaVaga(TODOS);
    setTipoDaPendencia(TODOS);
  }

  function decidir(item: Pendencia, qual: AcaoDoLider['acao']) {
    const aprovar = qual === 'aprovar';
    Alert.alert(aprovar ? 'Aprovar' : 'Recusar', aprovar ? item.aprovar : item.recusar, [
      { text: 'Voltar', style: 'cancel' },
      {
        text: aprovar ? 'Aprovar' : 'Recusar',
        style: aprovar ? 'default' : 'destructive',
        onPress: () =>
          acao.mutate(
            { ...item.pedido, acao: qual },
            {
              onSuccess: (resposta) => {
                if (!resposta?.vaga_id) return;
                const vagaId = resposta.vaga_id;
                Alert.alert('Vaga liberada', 'Quer escalar outra pessoa agora?', [
                  { text: 'Depois', style: 'cancel' },
                  { text: 'Escalar', onPress: () => abrirVaga(vagaId) },
                ]);
              },
            },
          ),
      },
    ]);
  }

  return (
    <Tela aoAtualizar={() => consulta.refetch()}>
      <Segmentos
        opcoes={[
          { valor: 'pendencias', rotulo: 'Pendências', total: lista.length },
          { valor: 'cultos', rotulo: 'Cultos' },
          { valor: 'vagas', rotulo: 'Vagas', total: vagas.data?.length },
        ]}
        valor={aba}
        aoEscolher={setEscolhida}
      />

      {aba === 'pendencias' && (
        <>
          <Estado consulta={pendencias} />
          <Erro erro={acao.error} />
          {pendencias.data && lista.length === 0 && (
            <Cartao>
              <Subtitulo>Tudo em dia 🙌</Subtitulo>
              <Suave>Nenhum impedimento, troca, oferta ou candidatura esperando você.</Suave>
            </Cartao>
          )}
          <FiltrosDoLider
            titulo="Filtrar pendências"
            nome="pendências"
            linhas={[
              { titulo: 'Tipo', todos: 'Todas', escolha: daPendencia.porTipo, aoEscolher: setTipoDaPendencia },
              { titulo: 'Equipe', todos: 'Todas', escolha: daPendencia.porEquipe, aoEscolher: setEquipe },
            ]}
            total={lista.length}
            mostrando={daPendencia.lista.length}
            aoLimpar={limparFiltros}
          />
          {daPendencia.lista.map((item) => {
            const emAndamento =
              acao.isPending && acao.variables?.tipo === item.pedido.tipo && acao.variables.id === item.pedido.id;
            return (
              <CartaoDePendencia
                key={item.chave}
                item={item}
                bloqueado={acao.isPending}
                carregando={emAndamento ? (acao.variables?.acao ?? null) : null}
                aoDecidir={(qual) => decidir(item, qual)}
              />
            );
          })}
        </>
      )}

      {aba === 'cultos' && (
        <>
          <Atalho
            icone="paper-plane-outline"
            texto="Pedir disponibilidade da equipe"
            aoTocar={() => router.push('/lider/disponibilidade')}
          />
          <Estado
            consulta={cultos}
            vazio={cultos.data?.length === 0 && 'Nenhum culto com escala da sua equipe nos próximos 60 dias.'}
          />
          <FiltrosDoLider
            titulo="Filtrar cultos"
            nome="cultos"
            linhas={[
              { titulo: 'Equipe', todos: 'Todas', escolha: doCulto.porEquipe, aoEscolher: setEquipe },
              { titulo: 'Quando', todos: 'Qualquer data', escolha: doCulto.porPeriodo, aoEscolher: setQuando },
              { titulo: 'Situação', todos: 'Todos', escolha: doCulto.porSituacao, aoEscolher: setSituacaoDoCulto },
            ]}
            total={cultos.data?.length ?? 0}
            mostrando={doCulto.lista.length}
            aoLimpar={limparFiltros}
          />
          {doCulto.lista.map((culto) => (
            <LinhaDeCulto key={culto.id} culto={culto} contagem={doCulto.contagem(culto)} />
          ))}
        </>
      )}

      {aba === 'vagas' && (
        <>
          <Estado consulta={vagas} vazio={vagas.data?.length === 0 && 'Nenhuma vaga em aberto nos próximos 60 dias.'} />
          <FiltrosDoLider
            titulo="Filtrar vagas"
            nome="vagas"
            linhas={[
              { titulo: 'Equipe', todos: 'Todas', escolha: daVaga.porEquipe, aoEscolher: setEquipe },
              { titulo: 'Quando', todos: 'Qualquer data', escolha: daVaga.porPeriodo, aoEscolher: setQuando },
              { titulo: 'Situação', todos: 'Todas', escolha: daVaga.porSituacao, aoEscolher: setSituacaoDaVaga },
            ]}
            total={vagas.data?.length ?? 0}
            mostrando={daVaga.lista.length}
            aoLimpar={limparFiltros}
          />
          {daVaga.lista.map((vaga) => (
            <Linha
              key={vaga.id}
              titulo={`${vaga.funcao} · ${vaga.evento.nome}`}
              detalhe={`${diaCurto(vaga.evento.data_inicio)} · ${vaga.equipe}`}
              status={resumoDaVaga(vaga)}
              corStatus={vaga.ofertas || vaga.disponiveis ? cores.confirmada : cores.pendente}
              aoTocar={() => abrirVaga(vaga.id)}
            />
          ))}
        </>
      )}
    </Tela>
  );
}

function CartaoDePendencia({
  item,
  bloqueado,
  carregando,
  aoDecidir,
}: {
  item: Pendencia;
  bloqueado: boolean;
  carregando: AcaoDoLider['acao'] | null;
  aoDecidir: (acao: AcaoDoLider['acao']) => void;
}) {
  const { cores } = useTema();
  return (
    <Cartao style={{ gap: 6 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <Subtitulo style={{ flex: 1 }}>{item.pessoa.nome}</Subtitulo>
        <Etiqueta {...item.tipo} />
      </View>
      {item.escala && (
        <Text numberOfLines={1} style={{ color: cores.textoSuave, fontSize: 13 }}>
          {item.escala.evento.nome} · {diaCurto(item.escala.evento.data_inicio)} · {item.escala.funcao}
        </Text>
      )}
      {!!item.detalhe && (
        <Text numberOfLines={2} style={{ color: cores.texto, fontSize: 14 }}>
          {item.detalhe}
        </Text>
      )}
      {item.link && (
        <Pressable
          onPress={item.link.abrir}
          hitSlop={6}
          accessibilityRole="link"
          style={({ pressed }) => [{ flexDirection: 'row', alignItems: 'center', gap: 4 }, pressed && { opacity: 0.6 }]}>
          <Text style={{ color: cores.primaria, fontSize: 14, fontWeight: '600' }}>{item.link.texto}</Text>
          <Ionicons name="chevron-forward" size={14} color={cores.primaria} />
        </Pressable>
      )}
      <View style={{ flexDirection: 'row', gap: 8, marginTop: 4 }}>
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
    </Cartao>
  );
}

function LinhaDeCulto({ culto, contagem }: { culto: Culto; contagem: ContagemDoCulto }) {
  const { cores } = useTema();
  const completo = !contagem.pendentes && !contagem.vagas;
  const escalados = contagem.total - contagem.vagas;
  const resumo = [
    escalados ? `${contagem.confirmadas}/${escalados} confirmadas` : null,
    contagem.vagas ? `${contagem.vagas} vaga${contagem.vagas === 1 ? '' : 's'}` : null,
  ]
    .filter(Boolean)
    .join(' · ');
  return (
    <Linha
      titulo={culto.nome}
      detalhe={diaCurto(culto.data_inicio)}
      status={completo ? 'Todos confirmados 🙌' : resumo}
      corStatus={completo ? cores.confirmada : cores.pendente}
      aoTocar={() => router.push({ pathname: '/lider/culto/[id]', params: { id: culto.id } })}
    />
  );
}

function Atalho({
  icone,
  texto,
  aoTocar,
}: {
  icone: ComponentProps<typeof Ionicons>['name'];
  texto: string;
  aoTocar: () => void;
}) {
  const { cores } = useTema();
  return (
    <Pressable
      onPress={aoTocar}
      accessibilityRole="button"
      hitSlop={6}
      style={({ pressed }) => [
        { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 4 },
        pressed && { opacity: 0.6 },
      ]}>
      <Ionicons name={icone} size={18} color={cores.primaria} />
      <Text style={{ color: cores.primaria, fontSize: 15, fontWeight: '600', flex: 1 }}>{texto}</Text>
      <Ionicons name="chevron-forward" size={16} color={cores.primaria} />
    </Pressable>
  );
}
