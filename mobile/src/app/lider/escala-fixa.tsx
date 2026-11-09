import Ionicons from '@expo/vector-icons/Ionicons';
import { useState } from 'react';
import { Alert, Pressable, Text, View } from 'react-native';

import { ChipsDeEscolha } from '../../lib/formulario-lider';
import {
  DadosDaLinha,
  MudancaNaEscalaFixa,
  useEscalaFixa,
  useMudarEscalaFixa,
  useOpcoesDeEventos,
} from '../../lib/hooks';
import { useTema } from '../../lib/tema';
import { LinhaDaEscalaFixa, Pessoa, ResultadoDaEscalaFixa, Turno } from '../../lib/types';
import {
  Avatar,
  Botao,
  Campo,
  Cartao,
  Erro,
  Estado,
  Grupo,
  ItemDeGrupo,
  Rotulo,
  Suave,
  Tela,
  Texto,
} from '../../lib/ui';

const DIAS = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo'];
// Domingo primeiro, como no calendário da igreja.
const ORDEM_DOS_DIAS = [6, 0, 1, 2, 3, 4, 5];
const TURNOS: { valor: Turno; rotulo: string }[] = [
  { valor: 'manha', rotulo: 'Manhã' },
  { valor: 'tarde', rotulo: 'Tarde' },
  { valor: 'noite', rotulo: 'Noite' },
];

/** "Todo domingo", "Toda quarta", "1º domingo", "3ª quarta". */
function rotuloDaSemana(dia: number, semana: number) {
  const feminino = dia < 5;
  if (semana === 0) return `${feminino ? 'Toda' : 'Todo'} ${DIAS[dia]}`;
  return `${semana}${feminino ? 'ª' : 'º'} ${DIAS[dia]}`;
}

// Sem digitar nada aparecem poucos nomes; digitando, um pouco mais.
const MAX_SEM_BUSCA = 5;
const MAX_RESULTADOS = 8;

/** Sem acento e em minúsculas, para a busca achar "joão" digitando "joao". */
const normalizar = (texto: string) =>
  texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

/**
 * Escolher a pessoa numa equipe grande: busca pelo nome com poucos resultados por vez.
 * Com alguém escolhido, mostra só essa pessoa e o botão "Trocar".
 */
function EscolherPessoa({
  membros,
  escolhida,
  aoEscolher,
}: {
  membros: Pessoa[];
  escolhida?: number;
  aoEscolher: (id: number) => void;
}) {
  const { cores } = useTema();
  const [busca, setBusca] = useState('');
  const [procurando, setProcurando] = useState(!escolhida);
  const pessoa = membros.find((m) => m.id === escolhida);

  if (pessoa && !procurando) {
    return (
      <View style={{ gap: 6 }}>
        <Rotulo>Pessoa</Rotulo>
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: 12,
            padding: 12,
            borderRadius: 12,
            borderWidth: 1,
            borderColor: cores.primaria,
          }}>
          <Avatar nome={pessoa.nome} destaque />
          <Text numberOfLines={1} style={{ flex: 1, fontSize: 16, fontWeight: '600', color: cores.texto }}>
            {pessoa.nome}
          </Text>
          <Pressable onPress={() => setProcurando(true)} hitSlop={10} accessibilityRole="button">
            <Text style={{ fontSize: 14, fontWeight: '600', color: cores.primaria }}>Trocar</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  const termo = normalizar(busca.trim());
  const encontrados = membros.filter((m) => normalizar(m.nome).includes(termo));
  const visiveis = encontrados.slice(0, termo ? MAX_RESULTADOS : MAX_SEM_BUSCA);
  const faltam = encontrados.length - visiveis.length;

  return (
    <View style={{ gap: 6 }}>
      <Campo
        rotulo="Pessoa"
        value={busca}
        onChangeText={setBusca}
        placeholder={`Buscar entre ${membros.length} integrante${membros.length === 1 ? '' : 's'}`}
        autoCorrect={false}
        autoFocus={procurando && !!escolhida}
      />
      <View style={{ borderRadius: 12, borderWidth: 1, borderColor: cores.borda, overflow: 'hidden' }}>
        {visiveis.map((m) => (
          <Pressable
            key={m.id}
            onPress={() => {
              aoEscolher(m.id);
              setBusca('');
              setProcurando(false);
            }}
            accessibilityRole="button"
            style={({ pressed }) => ({
              flexDirection: 'row',
              alignItems: 'center',
              gap: 12,
              paddingHorizontal: 12,
              paddingVertical: 10,
              borderBottomWidth: 1,
              borderBottomColor: cores.borda,
              backgroundColor: pressed ? cores.fundo : undefined,
            })}>
            <Avatar nome={m.nome} />
            <Text numberOfLines={1} style={{ flex: 1, fontSize: 15, color: cores.texto }}>
              {m.nome}
            </Text>
          </Pressable>
        ))}
        {visiveis.length === 0 && <Suave style={{ padding: 12 }}>Ninguém encontrado com esse nome.</Suave>}
        {faltam > 0 && (
          <Suave style={{ padding: 12, fontSize: 13 }}>
            E mais {faltam} pessoa{faltam === 1 ? '' : 's'}: digite o nome para encontrar.
          </Suave>
        )}
      </View>
      {pessoa && (
        <Pressable onPress={() => setProcurando(false)} hitSlop={8} accessibilityRole="button">
          <Text style={{ fontSize: 14, fontWeight: '600', color: cores.textoSuave }}>Manter {pessoa.nome}</Text>
        </Pressable>
      )}
    </View>
  );
}

type Edicao = { id?: number } & Partial<DadosDaLinha>;

/** Mensagem para o líder depois de salvar: o resumo e quem não pôde ser escalado. */
function mostrarResultado(resultado: ResultadoDaEscalaFixa) {
  const puladas = resultado.puladas
    .slice(0, 4)
    .map((p) => {
      const data = new Date(p.data).toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit' });
      return `• ${p.pessoa} em ${data}: ${p.motivo}`;
    })
    .join('\n');
  Alert.alert(
    'Escala fixa salva',
    puladas ? `${resultado.resumo}\n\n${puladas}\n\nEssas vagas ficaram em aberto.` : resultado.resumo,
  );
}

/**
 * Escala fixa da equipe: o líder diz uma vez quem serve em cada culto e os cultos cadastrados
 * (e os próximos) são preenchidos sozinhos. Mesmas regras do site (escala/fixa.py).
 */
export default function EscalaFixaDaEquipe() {
  const opcoes = useOpcoesDeEventos();
  const [escolhida, setEscolhida] = useState<number>();
  const equipeId = escolhida ?? opcoes.data?.equipes[0]?.id;
  const consulta = useEscalaFixa(equipeId);
  const mudar = useMudarEscalaFixa();
  const { cores } = useTema();
  const [edicao, setEdicao] = useState<Edicao | null>(null);
  const dados = consulta.data;

  function executar(mudanca: MudancaNaEscalaFixa) {
    mudar.mutate(mudanca, {
      onSuccess: (resultado) => {
        setEdicao(null);
        if (mudanca.tipo === 'ligar' && !mudanca.ativa) {
          Alert.alert('Escala fixa desligada', 'Os cultos já preenchidos continuam como estão.');
        } else if (resultado) mostrarResultado(resultado);
      },
    });
  }

  function ligar(ativa: boolean) {
    if (!equipeId) return;
    Alert.alert(
      ativa ? 'Ligar escala fixa' : 'Desligar escala fixa',
      ativa
        ? 'Os cultos já cadastrados com as funções da equipe são preenchidos com as linhas abaixo e cada pessoa recebe um aviso.'
        : 'A equipe volta a ser flexível. Os cultos já preenchidos continuam como estão.',
      [
        { text: 'Voltar', style: 'cancel' },
        { text: ativa ? 'Ligar' : 'Desligar', onPress: () => executar({ tipo: 'ligar', equipeId, ativa }) },
      ],
    );
  }

  function salvar() {
    if (!edicao || !equipeId) return;
    const { id, dia_semana, turno, semana, funcao_id, usuario_id } = edicao;
    if (dia_semana === undefined || !turno || semana === undefined || !funcao_id || !usuario_id) return;
    const linha = { dia_semana, turno, semana, funcao_id, usuario_id };
    if (id === undefined) {
      executar({ tipo: 'adicionar', equipeId, linha });
      return;
    }
    Alert.alert('Salvar mudança', 'Os cultos que esta linha já preencheu e ainda não foram confirmados mudam junto.', [
      { text: 'Voltar', style: 'cancel' },
      { text: 'Salvar', onPress: () => executar({ tipo: 'editar', id, linha }) },
    ]);
  }

  function excluir(id: number) {
    Alert.alert(
      'Excluir linha',
      'Os cultos que ela preencheu e ainda não foram confirmados ficam com a vaga em aberto.',
      [
        { text: 'Voltar', style: 'cancel' },
        { text: 'Excluir', style: 'destructive', onPress: () => executar({ tipo: 'excluir', id }) },
      ],
    );
  }

  function editar(item: LinhaDaEscalaFixa) {
    setEdicao({
      id: item.id,
      dia_semana: item.dia_semana,
      turno: item.turno,
      semana: item.semana,
      funcao_id: item.funcao.id,
      usuario_id: item.usuario.id,
    });
  }

  // Linhas agrupadas por culto ("Domingo de manhã"), na ordem da semana da igreja.
  const grupos: { culto: string; itens: LinhaDaEscalaFixa[] }[] = [];
  if (dados) {
    const ordenados = [...dados.itens].sort(
      (a, b) =>
        ORDEM_DOS_DIAS.indexOf(a.dia_semana) - ORDEM_DOS_DIAS.indexOf(b.dia_semana) ||
        TURNOS.findIndex((t) => t.valor === a.turno) - TURNOS.findIndex((t) => t.valor === b.turno) ||
        a.semana - b.semana,
    );
    for (const item of ordenados) {
      const grupo = grupos.find((g) => g.culto === item.culto);
      if (grupo) grupo.itens.push(item);
      else grupos.push({ culto: item.culto, itens: [item] });
    }
  }

  const completa =
    !!edicao &&
    edicao.dia_semana !== undefined &&
    !!edicao.turno &&
    edicao.semana !== undefined &&
    !!edicao.funcao_id &&
    !!edicao.usuario_id;

  return (
    <Tela aoAtualizar={() => consulta.refetch()}>
      <Estado consulta={opcoes} vazio={opcoes.data?.equipes.length === 0 && 'Você não lidera nenhuma equipe.'} />
      {opcoes.data && opcoes.data.equipes.length > 1 && (
        <Cartao>
          <ChipsDeEscolha
            titulo="Equipe"
            opcoes={opcoes.data.equipes.map((e) => ({ valor: e.id, rotulo: e.nome }))}
            ativas={equipeId ? [equipeId] : []}
            aoTocar={(id) => {
              setEscolhida(id);
              setEdicao(null);
            }}
          />
        </Cartao>
      )}
      {equipeId && <Estado consulta={consulta} />}

      {dados && (
        <>
          <Cartao style={{ gap: 10 }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
              <View
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: 5,
                  backgroundColor: dados.ativa ? cores.confirmada : cores.textoSuave,
                }}
              />
              <Text style={{ flex: 1, fontSize: 16, fontWeight: '700', color: cores.texto }}>
                {dados.ativa ? 'Escala fixa ligada' : 'Escala fixa desligada'}
              </Text>
            </View>
            <Suave>
              {dados.ativa
                ? 'Os cultos com as funções da equipe são preenchidos sozinhos, inclusive os próximos. Cada pessoa é avisada e confirma, pede impedimento ou troca normalmente.'
                : 'A equipe é flexível: você escala culto a culto. Monte as linhas abaixo e ligue quando estiver pronto.'}
            </Suave>
            <Botao
              titulo={dados.ativa ? 'Desligar escala fixa' : 'Ligar escala fixa'}
              variante={dados.ativa ? 'secundario' : undefined}
              carregando={mudar.isPending && mudar.variables?.tipo === 'ligar'}
              desabilitado={!dados.ativa && dados.itens.length === 0}
              aoTocar={() => ligar(!dados.ativa)}
            />
          </Cartao>

          {!edicao && <Erro erro={mudar.error} />}

          {edicao && (
            <Cartao style={{ gap: 14, borderColor: cores.primaria }}>
              <Texto style={{ fontWeight: '700' }}>{edicao.id ? 'Editar linha' : 'Nova linha'}</Texto>
              <ChipsDeEscolha
                titulo="Dia"
                opcoes={ORDEM_DOS_DIAS.map((d) => ({
                  valor: d,
                  rotulo: DIAS[d].charAt(0).toUpperCase() + DIAS[d].slice(1),
                }))}
                ativas={edicao.dia_semana !== undefined ? [edicao.dia_semana] : []}
                aoTocar={(dia_semana) => setEdicao({ ...edicao, dia_semana })}
              />
              <ChipsDeEscolha
                titulo="Turno"
                opcoes={TURNOS}
                ativas={edicao.turno ? [edicao.turno as Turno] : []}
                aoTocar={(turno) => setEdicao({ ...edicao, turno })}
              />
              <ChipsDeEscolha
                titulo="Quando"
                opcoes={[0, 1, 2, 3, 4, 5].map((s) => ({
                  valor: s,
                  rotulo: rotuloDaSemana(edicao.dia_semana ?? 6, s),
                }))}
                ativas={edicao.semana !== undefined ? [edicao.semana] : []}
                aoTocar={(semana) => setEdicao({ ...edicao, semana })}
                dica={`Um dia específico (ex.: ${rotuloDaSemana(edicao.dia_semana ?? 6, 1)}) vale no lugar de “${rotuloDaSemana(edicao.dia_semana ?? 6, 0)}” da mesma função naquele dia.`}
              />
              {dados.funcoes.length === 0 ? (
                <Suave>Cadastre as funções em Gerenciar equipe antes.</Suave>
              ) : (
                <ChipsDeEscolha
                  titulo="Função"
                  opcoes={dados.funcoes.map((f) => ({ valor: f.id, rotulo: f.nome }))}
                  ativas={edicao.funcao_id ? [edicao.funcao_id] : []}
                  aoTocar={(funcao_id) => setEdicao({ ...edicao, funcao_id })}
                />
              )}
              <EscolherPessoa
                key={edicao.id ?? 'nova'}
                membros={dados.membros}
                escolhida={edicao.usuario_id}
                aoEscolher={(usuario_id) => setEdicao({ ...edicao, usuario_id })}
              />
              <Erro erro={mudar.error} />
              <Botao titulo="Salvar" desabilitado={!completa} carregando={mudar.isPending} aoTocar={salvar} />
              {edicao.id !== undefined && (
                <Botao titulo="Excluir linha" variante="perigo" aoTocar={() => excluir(edicao.id!)} />
              )}
              <Botao titulo="Cancelar" variante="secundario" aoTocar={() => setEdicao(null)} />
            </Cartao>
          )}

          {!edicao && (
            <Grupo>
              <ItemDeGrupo
                icone="add-circle-outline"
                titulo="Adicionar linha"
                aoTocar={() => {
                  setEdicao({ dia_semana: 6, turno: 'manha', semana: 0 });
                }}
              />
            </Grupo>
          )}

          {grupos.length === 0 && !edicao && (
            <Cartao>
              <Suave>
                Nenhuma linha ainda. Exemplo: “Domingo de manhã · Todo domingo · Som · Fulano”. Para alternar pessoas,
                use “1º domingo”, “2º domingo”…
              </Suave>
            </Cartao>
          )}

          {grupos.map((grupo) => (
            <Grupo key={grupo.culto} titulo={grupo.culto}>
              {grupo.itens.map((item) => (
                <Pressable
                  key={item.id}
                  onPress={() => editar(item)}
                  accessibilityRole="button"
                  style={({ pressed }) => ({
                    flexDirection: 'row',
                    alignItems: 'center',
                    gap: 12,
                    paddingHorizontal: 16,
                    paddingVertical: 12,
                    borderBottomWidth: 1,
                    borderBottomColor: cores.borda,
                    backgroundColor: pressed || edicao?.id === item.id ? cores.fundo : undefined,
                  })}>
                  <View style={{ flex: 1, gap: 2 }}>
                    <Text numberOfLines={1} style={{ fontSize: 16, fontWeight: '600', color: cores.texto }}>
                      {item.funcao.nome} · {item.usuario.nome}
                    </Text>
                    <Rotulo style={{ textTransform: 'none', letterSpacing: 0, fontSize: 13, fontWeight: '500' }}>
                      {item.quando}
                    </Rotulo>
                  </View>
                  <Ionicons name="create-outline" size={18} color={cores.textoSuave} />
                </Pressable>
              ))}
            </Grupo>
          ))}
        </>
      )}
    </Tela>
  );
}
