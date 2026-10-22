import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, View } from 'react-native';

import { mesPorExtenso, periodo } from '../../lib/datas';
import { useEventosElegiveis, useMudarDisponibilidades } from '../../lib/hooks';
import { useTema } from '../../lib/tema';
import { EventoComEquipe } from '../../lib/types';
import { Botao, Cartao, Erro, Estado, Opcoes, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

type Tipo = 'domingo-manha' | 'domingo-noite' | 'quarta' | 'outros';

const ROTULO_DO_TIPO: Record<Tipo, string> = {
  'domingo-manha': 'Domingo manhã',
  'domingo-noite': 'Domingo noite',
  quarta: 'Quarta',
  outros: 'Outros',
};

/** Tipo do culto pelo dia da semana e horário de início (no fuso do aparelho), não pelo nome. */
function tipoDoEvento(evento: EventoComEquipe): Tipo {
  const inicio = new Date(evento.data_inicio);
  if (inicio.getDay() === 0) return inicio.getHours() < 14 ? 'domingo-manha' : 'domingo-noite';
  if (inicio.getDay() === 3) return 'quarta';
  return 'outros';
}

const chaveDoMes = (evento: EventoComEquipe) => evento.data_inicio.slice(0, 7);
const chaveDaEquipe = (evento: EventoComEquipe) => (evento.equipe_id ? String(evento.equipe_id) : 'gerais');

/** Opções de um filtro: "todos" mais os valores presentes na lista, na ordem em que aparecem. */
function opcoesDe(
  eventos: EventoComEquipe[],
  chave: (e: EventoComEquipe) => string,
  rotulo: (e: EventoComEquipe) => string,
  rotuloTodos: string,
) {
  const vistas = new Map<string, string>();
  for (const evento of eventos) if (!vistas.has(chave(evento))) vistas.set(chave(evento), rotulo(evento));
  return [{ valor: 'todos', rotulo: rotuloTodos }, ...[...vistas].map(([valor, r]) => ({ valor, rotulo: r }))];
}

/** "Equipe Recepção", sem repetir a palavra quando o nome já começa com "Equipe". */
const nomeDaEquipe = (nome: string) => (/^equipe\b/i.test(nome) ? nome : `Equipe ${nome}`);

/** Uma linha de filtro com título, para deixar claro o que as opções filtram. */
function Filtro({
  titulo,
  opcoes,
  valor,
  aoEscolher,
}: {
  titulo: string;
  opcoes: { valor: string; rotulo: string }[];
  valor: string;
  aoEscolher: (valor: string) => void;
}) {
  if (opcoes.length <= 2) return null; // uma opção só não filtra nada
  return (
    <View style={{ gap: 6 }}>
      <Suave style={{ fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 }}>{titulo}</Suave>
      <Opcoes opcoes={opcoes} valor={valor} aoEscolher={aoEscolher} />
    </View>
  );
}

export default function PorEvento() {
  const eventos = useEventosElegiveis();
  const mudar = useMudarDisponibilidades();
  const { cores } = useTema();
  const [marcados, setMarcados] = useState<number[]>([]);
  const [mes, setMes] = useState('todos');
  const [tipo, setTipo] = useState('todos');
  const [equipe, setEquipe] = useState('todos');

  const lista = eventos.data ?? [];
  const filtros = useMemo(() => {
    const ordemDosTipos = Object.keys(ROTULO_DO_TIPO);
    const tipos = opcoesDe(lista, tipoDoEvento, (e) => ROTULO_DO_TIPO[tipoDoEvento(e)], 'Todos os cultos');
    tipos.sort((a, b) => (a.valor === 'todos' ? -1 : b.valor === 'todos' ? 1 : ordemDosTipos.indexOf(a.valor) - ordemDosTipos.indexOf(b.valor)));
    return {
      meses: opcoesDe(lista, chaveDoMes, (e) => mesPorExtenso(e.data_inicio), 'Todos os meses'),
      tipos,
      equipes: opcoesDe(lista, chaveDaEquipe, (e) => (e.equipe ? nomeDaEquipe(e.equipe) : 'Cultos gerais'), 'Todas'),
    };
  }, [lista]);

  const visiveis = lista.filter(
    (e) =>
      (mes === 'todos' || chaveDoMes(e) === mes) &&
      (tipo === 'todos' || tipoDoEvento(e) === tipo) &&
      (equipe === 'todos' || chaveDaEquipe(e) === equipe),
  );
  const filtrando = mes !== 'todos' || tipo !== 'todos' || equipe !== 'todos';
  const temFiltros = [filtros.meses, filtros.tipos, filtros.equipes].some((o) => o.length > 2);
  function limparFiltros() {
    setMes('todos');
    setTipo('todos');
    setEquipe('todos');
  }
  const todosVisiveisMarcados = visiveis.length > 0 && visiveis.every((e) => marcados.includes(e.id));

  const alternar = (id: number) =>
    setMarcados((atual) => (atual.includes(id) ? atual.filter((i) => i !== id) : [...atual, id]));

  // Marcar/desmarcar vale só para o que está visível no filtro; o resto da seleção é mantido.
  function alternarVisiveis() {
    const ids = visiveis.map((e) => e.id);
    setMarcados((atual) =>
      todosVisiveisMarcados ? atual.filter((id) => !ids.includes(id)) : [...new Set([...atual, ...ids])],
    );
  }

  return (
    <Tela atualizando={eventos.isRefetching} aoAtualizar={() => eventos.refetch()}>
      <Texto>Marque os eventos dos próximos 60 dias em que você pode servir.</Texto>
      <Estado consulta={eventos} vazio={eventos.data?.length === 0 && 'Não há eventos novos para marcar.'} />

      {lista.length > 0 && (
        <>
          {temFiltros && (
            <Cartao style={{ gap: 12 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <Ionicons name="funnel-outline" size={18} color={cores.texto} />
                  <Subtitulo>Filtrar eventos</Subtitulo>
                </View>
                {filtrando && (
                  <Pressable onPress={limparFiltros} hitSlop={8} accessibilityRole="button">
                    <Suave style={{ color: cores.primaria, fontWeight: '600' }}>Limpar filtros</Suave>
                  </Pressable>
                )}
              </View>
              <Filtro titulo="Mês" opcoes={filtros.meses} valor={mes} aoEscolher={setMes} />
              <Filtro titulo="Culto" opcoes={filtros.tipos} valor={tipo} aoEscolher={setTipo} />
              <Filtro titulo="Equipe" opcoes={filtros.equipes} valor={equipe} aoEscolher={setEquipe} />
            </Cartao>
          )}

          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <Suave>
              {filtrando ? `Mostrando ${visiveis.length} de ${lista.length}` : `${lista.length} eventos`} ·{' '}
              {marcados.length} selecionado{marcados.length === 1 ? '' : 's'}
            </Suave>
            {visiveis.length > 0 && (
              <Pressable onPress={alternarVisiveis} hitSlop={8} accessibilityRole="button">
                <Suave style={{ color: cores.primaria, fontWeight: '600' }}>
                  {todosVisiveisMarcados ? 'Desmarcar todos' : 'Marcar todos'}
                </Suave>
              </Pressable>
            )}
          </View>
        </>
      )}

      {lista.length > 0 && visiveis.length === 0 && (
        <Suave style={{ textAlign: 'center', marginTop: 16 }}>Nenhum evento com esses filtros.</Suave>
      )}

      {visiveis.map((evento) => {
        const marcado = marcados.includes(evento.id);
        return (
          <Pressable
            key={evento.id}
            onPress={() => alternar(evento.id)}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: marcado }}>
            <Cartao style={marcado ? { borderColor: cores.primaria } : undefined}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                <Ionicons
                  name={marcado ? 'checkbox' : 'square-outline'}
                  size={26}
                  color={marcado ? cores.primaria : cores.textoSuave}
                />
                <View style={{ flex: 1, gap: 2 }}>
                  <Subtitulo>{evento.nome}</Subtitulo>
                  <Suave>{periodo(evento.data_inicio, evento.data_fim)}</Suave>
                  {!!evento.equipe && <Suave>{nomeDaEquipe(evento.equipe)}</Suave>}
                </View>
              </View>
            </Cartao>
          </Pressable>
        );
      })}

      <Erro erro={mudar.error} />
      {lista.length > 0 && (
        <Botao
          titulo={marcados.length ? `Salvar (${marcados.length})` : 'Salvar'}
          desabilitado={marcados.length === 0}
          carregando={mudar.isPending}
          aoTocar={() =>
            mudar.mutate({ acao: 'por-evento', evento_ids: marcados }, { onSuccess: () => router.back() })
          }
        />
      )}
    </Tela>
  );
}
